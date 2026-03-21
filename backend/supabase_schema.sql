-- AnemiaLens — Supabase Schema
-- Run this in Supabase SQL Editor to create all tables

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    uid VARCHAR(36) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(32) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    scan_count INTEGER NOT NULL DEFAULT 0,
    subscription_tier VARCHAR(32) NOT NULL DEFAULT 'free',
    stripe_customer_id VARCHAR(128) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_users_uid ON users(uid);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id ON users(stripe_customer_id);

CREATE TABLE IF NOT EXISTS screenings (
    id SERIAL PRIMARY KEY,
    uid VARCHAR(36) UNIQUE NOT NULL,
    user_id INTEGER,
    request_id VARCHAR(16) NOT NULL,
    triage_band VARCHAR(32) NOT NULL,
    triage_score FLOAT NOT NULL,
    triage_label VARCHAR(64) NOT NULL,
    anemia_risk FLOAT,
    predicted_hemoglobin FLOAT,
    confidence FLOAT,
    uncertainty FLOAT,
    screening_label VARCHAR(32),
    model_source VARCHAR(64),
    quality_passed BOOLEAN NOT NULL DEFAULT TRUE,
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    processing_path VARCHAR(32) NOT NULL DEFAULT 'roi_crop',
    guidance_source VARCHAR(16) NOT NULL DEFAULT 'fallback',
    symptoms_json TEXT,
    full_response_json TEXT,
    share_text TEXT,
    urgency_label VARCHAR(128),
    headline VARCHAR(255),
    processing_time_ms FLOAT NOT NULL DEFAULT 0.0,
    language VARCHAR(16),
    region VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_screenings_uid ON screenings(uid);
CREATE INDEX IF NOT EXISTS ix_screenings_user_id ON screenings(user_id);
CREATE INDEX IF NOT EXISTS ix_screenings_created_at ON screenings(created_at);
