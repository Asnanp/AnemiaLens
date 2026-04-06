-- =====================================================
-- AnemiaLens Database Schema Enhancement
-- Production-ready schema with indexing, analytics, and audit capabilities
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for encryption functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- Core Tables (Already Exist - Enhanced Version)
-- =====================================================

-- Users table (enhanced)
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    uid UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin', 'clinician')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    scan_count INTEGER NOT NULL DEFAULT 0,
    subscription_tier VARCHAR(50) NOT NULL DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'enterprise')),
    stripe_customer_id VARCHAR(255),
    
    -- Enhanced fields
    phone VARCHAR(50),
    date_of_birth DATE,
    ethnicity VARCHAR(100),
    locale VARCHAR(10) NOT NULL DEFAULT 'en',
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    last_login_at TIMESTAMPTZ,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    mfa_enabled BOOLEAN NOT NULL DEFAULT false,
    mfa_secret TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ, -- Soft delete
    
    -- Indexes for performance
    CONSTRAINT users_email_check CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Screenings table (enhanced)
CREATE TABLE IF NOT EXISTS screenings (
    id BIGSERIAL PRIMARY KEY,
    uid UUID NOT NULL DEFAULT uuid_generate_v4() UNIQUE,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    
    -- Core screening data
    image_url TEXT NOT NULL,
    predicted_hemoglobin DECIMAL(5, 2),
    anemia_risk DECIMAL(5, 4),
    confidence_score DECIMAL(5, 4),
    triage_band VARCHAR(50),
    
    -- Quality metrics
    image_quality_score DECIMAL(5, 4),
    quality_passed BOOLEAN NOT NULL DEFAULT false,
    quality_issues JSONB,
    
    -- Clinical data
    symptoms JSONB,
    patient_profile JSONB,
    clinical_brief JSONB,
    guidance TEXT,
    
    -- ML metadata
    model_version VARCHAR(50),
    inference_time_ms INTEGER,
    calibration_applied BOOLEAN NOT NULL DEFAULT false,
    
    -- Workflow tracking
    workflow_stage VARCHAR(50) NOT NULL DEFAULT 'completed',
    handoff_sent BOOLEAN NOT NULL DEFAULT false,
    
    -- Metadata
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ -- Soft delete
);

-- =====================================================
-- Analytics Tables
-- =====================================================

-- Screening analytics for business intelligence
CREATE TABLE IF NOT EXISTS screening_analytics (
    id BIGSERIAL PRIMARY KEY,
    screening_id UUID NOT NULL REFERENCES screenings(uid) ON DELETE CASCADE,
    
    -- Performance metrics
    total_processing_time_ms INTEGER,
    quality_check_time_ms INTEGER,
    inference_time_ms INTEGER,
    guidance_generation_time_ms INTEGER,
    
    -- Model performance
    model_predictions JSONB,
    ensemble_weights JSONB,
    calibration_delta DECIMAL(5, 4),
    
    -- User behavior
    time_to_upload INTEGER, -- seconds from page load to upload
    time_to_complete INTEGER, -- total screening time
    steps_completed INTEGER,
    abandoned_at_step INTEGER, -- NULL if completed
    
    -- Device/browser info
    device_type VARCHAR(50),
    browser_name VARCHAR(50),
    os_name VARCHAR(50),
    
    -- Geographic
    country VARCHAR(100),
    region VARCHAR(100),
    city VARCHAR(100),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Model performance tracking
CREATE TABLE IF NOT EXISTS model_performance (
    id BIGSERIAL PRIMARY KEY,
    model_version VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    
    -- Performance metrics
    accuracy DECIMAL(5, 4),
    precision DECIMAL(5, 4),
    recall DECIMAL(5, 4),
    f1_score DECIMAL(5, 4),
    auc_roc DECIMAL(5, 4),
    
    -- Calibration metrics
    expected_calibration_error DECIMAL(5, 4),
    brier_score DECIMAL(5, 4),
    
    -- Demographic breakdown
    demographic_metrics JSONB,
    
    -- Data
    sample_size INTEGER,
    evaluation_date DATE NOT NULL,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(model_version, evaluation_date)
);

-- A/B test tracking
CREATE TABLE IF NOT EXISTS ab_tests (
    id BIGSERIAL PRIMARY KEY,
    test_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    
    -- Test configuration
    variant_a VARCHAR(100) NOT NULL,
    variant_b VARCHAR(100) NOT NULL,
    traffic_split DECIMAL(5, 2) NOT NULL DEFAULT 50.00, -- percentage for variant B
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'completed', 'cancelled')),
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    
    -- Results
    winner VARCHAR(100),
    statistical_significance DECIMAL(5, 4),
    results JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- A/B test assignments
CREATE TABLE IF NOT EXISTS ab_test_assignments (
    id BIGSERIAL PRIMARY KEY,
    test_id BIGINT NOT NULL REFERENCES ab_tests(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    screening_id UUID REFERENCES screenings(uid) ON DELETE CASCADE,
    
    variant VARCHAR(100) NOT NULL CHECK (variant IN ('A', 'B')),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(test_id, screening_id)
);

-- =====================================================
-- Audit & Compliance Tables
-- =====================================================

-- HIPAA audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    
    -- Event details
    event_type VARCHAR(100) NOT NULL,
    event_subtype VARCHAR(100),
    
    -- User context
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    
    -- Resource context
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    
    -- Request context
    ip_address INET,
    user_agent TEXT,
    correlation_id UUID,
    
    -- Event data
    details JSONB,
    
    -- Compliance
    break_glass BOOLEAN NOT NULL DEFAULT false,
    justification TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Data access log (for compliance reporting)
CREATE TABLE IF NOT EXISTS data_access_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- Notification System
-- =====================================================

CREATE TABLE IF NOT EXISTS notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Metadata
    data JSONB,
    
    -- Status
    read BOOLEAN NOT NULL DEFAULT false,
    read_at TIMESTAMPTZ,
    
    -- Priority
    priority VARCHAR(50) NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- Indexes for Performance
-- =====================================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_uid ON users(uid);
CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_tier) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_at) WHERE last_login_at IS NOT NULL;

-- Screenings indexes (critical for query performance)
CREATE INDEX IF NOT EXISTS idx_screenings_user_id ON screenings(user_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_screenings_uid ON screenings(uid);
CREATE INDEX IF NOT EXISTS idx_screenings_created_at ON screenings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_screenings_triage_band ON screenings(triage_band);
CREATE INDEX IF NOT EXISTS idx_screenings_user_created ON screenings(user_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_screenings_quality_passed ON screenings(quality_passed);
CREATE INDEX IF NOT EXISTS idx_screenings_model_version ON screenings(model_version);

-- Analytics indexes
CREATE INDEX IF NOT EXISTS idx_screening_analytics_screening_id ON screening_analytics(screening_id);
CREATE INDEX IF NOT EXISTS idx_screening_analytics_created_at ON screening_analytics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_screening_analytics_device_type ON screening_analytics(device_type);

-- Audit log indexes
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- Notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id) WHERE read = false;
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(user_id, created_at DESC);

-- =====================================================
-- Triggers for Automatic Updates
-- =====================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_screenings_updated_at BEFORE UPDATE ON screenings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ab_tests_updated_at BEFORE UPDATE ON ab_tests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Views for Common Queries
-- =====================================================

-- Active users in last 30 days
CREATE OR REPLACE VIEW active_users_30d AS
SELECT 
    u.id,
    u.uid,
    u.email,
    u.full_name,
    u.subscription_tier,
    u.last_login_at,
    COUNT(s.id) as screenings_last_30d
FROM users u
LEFT JOIN screenings s ON u.id = s.user_id 
    AND s.created_at >= NOW() - INTERVAL '30 days'
    AND s.deleted_at IS NULL
WHERE u.is_active = true
    AND u.deleted_at IS NULL
    AND u.last_login_at >= NOW() - INTERVAL '30 days'
GROUP BY u.id
ORDER BY u.last_login_at DESC;

-- Screening statistics by day
CREATE OR REPLACE VIEW daily_screening_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_screenings,
    COUNT(*) FILTER (WHERE quality_passed = true) as quality_passed,
    COUNT(*) FILTER (WHERE quality_passed = false) as quality_failed,
    AVG(predicted_hemoglobin) as avg_hemoglobin,
    AVG(anemia_risk) as avg_risk,
    COUNT(*) FILTER (WHERE triage_band = 'high_concern') as high_concern,
    COUNT(*) FILTER (WHERE triage_band = 'moderate_risk') as moderate_risk,
    COUNT(*) FILTER (WHERE triage_band = 'low_risk') as low_risk
FROM screenings
WHERE deleted_at IS NULL
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Model performance summary
CREATE OR REPLACE VIEW model_performance_summary AS
SELECT 
    model_version,
    COUNT(*) as total_predictions,
    AVG(anemia_risk) as avg_risk_score,
    AVG(confidence_score) as avg_confidence,
    AVG(inference_time_ms) as avg_inference_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY inference_time_ms) as p95_inference_time
FROM screenings
WHERE model_version IS NOT NULL
    AND deleted_at IS NULL
GROUP BY model_version
ORDER BY total_predictions DESC;

-- =====================================================
-- Row Level Security (RLS) Policies
-- =====================================================

-- Enable RLS on sensitive tables
ALTER TABLE screenings ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Users can only see their own screenings
CREATE POLICY users_see_own_screenings ON screenings
    FOR SELECT
    USING (user_id = auth.uid());

-- Users can only see their own notifications
CREATE POLICY users_see_own_notifications ON notifications
    FOR ALL
    USING (user_id = auth.uid());

-- Audit log is append-only (no updates/deletes)
CREATE POLICY audit_log_append_only ON audit_log
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY audit_log_read_admin ON audit_log
    FOR SELECT
    USING (auth.jwt() ->> 'role' = 'admin');

-- =====================================================
-- Comments for Documentation
-- =====================================================

COMMENT ON TABLE users IS 'User accounts with authentication and profile data';
COMMENT ON TABLE screenings IS 'Medical screening records with ML predictions';
COMMENT ON TABLE screening_analytics IS 'Business intelligence analytics for screenings';
COMMENT ON TABLE model_performance IS 'Model evaluation metrics and performance tracking';
COMMENT ON TABLE ab_tests IS 'A/B test configurations and results';
COMMENT ON TABLE audit_log IS 'HIPAA-compliant audit trail for all PHI access';
COMMENT ON TABLE notifications IS 'User notifications and alerts';

COMMENT ON COLUMN screenings.predicted_hemoglobin IS 'Predicted hemoglobin level in g/dL';
COMMENT ON COLUMN screenings.anemia_risk IS 'Anemia risk score (0.0-1.0)';
COMMENT ON COLUMN screenings.triage_band IS 'Triage category: low_risk, moderate_risk, high_concern';
COMMENT ON COLUMN screenings.model_version IS 'ML model version used for prediction';

-- =====================================================
-- Initial Data
-- =====================================================

-- Insert default model performance tracking
INSERT INTO model_performance (model_version, model_name, evaluation_date)
VALUES 
    ('v7-ultimate-clinical', 'Archive Fusion v7', CURRENT_DATE),
    ('v8-clinical', 'Archive Fusion v8', CURRENT_DATE)
ON CONFLICT (model_version, evaluation_date) DO NOTHING;
