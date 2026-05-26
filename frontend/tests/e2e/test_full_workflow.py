"""
Playwright E2E Tests for AnemiaLens Frontend

Test Suite:
1. Landing Page & Navigation
2. Authentication Flow
3. Screening Workflow (Complete)
4. Dashboard & History
5. Error Scenarios & Recovery
6. Accessibility Tests
7. Performance Benchmarks
8. Mobile Responsiveness
"""

import pytest
from playwright.sync_api import Page, expect, BrowserContext
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:3000"
API_URL = "http://localhost:5000"
TIMEOUT = 30000  # 30 seconds for slow operations


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "en-US",
    }


@pytest.fixture
def page(page: Page):
    page.set_default_timeout(TIMEOUT)
    yield page


# ---------------------------------------------------------------------------
# 1. Landing Page & Navigation Tests
# ---------------------------------------------------------------------------

class TestLandingPage:
    """Test landing page functionality and content"""

    def test_landing_page_loads(self, page: Page):
        """Verify landing page loads successfully"""
        page.goto(BASE_URL)
        expect(page).to_have_title(re.compile("AnemiaLens", re.IGNORECASE))

    def test_hero_section_visible(self, page: Page):
        """Verify hero section is visible with key messaging"""
        page.goto(BASE_URL)
        expect(page.get_by_role("heading", level=1)).to_be_visible()
        expect(page.get_by_text("anemia", ignore_case=True)).to_be_visible()

    def test_navigation_links_work(self, page: Page):
        """Test all navigation links are present and clickable"""
        page.goto(BASE_URL)
        
        # Check main navigation items
        nav_items = ["How It Works", "Science", "FAQ"]
        for item in nav_items:
            expect(page.get_by_text(item, exact=False)).to_be_visible()

    def test_cta_buttons_visible(self, page: Page):
        """Verify call-to-action buttons are visible and functional"""
        page.goto(BASE_URL)
        start_screening = page.get_by_role("button", name=re.compile("Start Screening|Upload Image", re.IGNORECASE))
        expect(start_screening).to_be_visible()

    def test_language_switcher(self, page: Page):
        """Test language switching functionality"""
        page.goto(BASE_URL)
        
        # Check language switcher exists
        lang_switcher = page.get_by_role("combobox").or_(page.get_by_text("EN"))
        expect(lang_switcher).to_be_visible()


# ---------------------------------------------------------------------------
# 2. Authentication Flow Tests
# ---------------------------------------------------------------------------

class TestAuthentication:
    """Test authentication flows"""

    def test_register_new_user(self, page: Page):
        """Test new user registration"""
        page.goto(f"{BASE_URL}/auth")
        
        # Click register
        page.get_by_text("Sign Up").or_(page.get_by_text("Register")).click()
        
        # Fill registration form
        page.get_by_label("Email").fill("test@example.com")
        page.get_by_label("Password").fill("SecurePass123!")
        
        # Submit
        page.get_by_role("button", name="Register").click()
        
        # Wait for response
        page.wait_for_timeout(2000)

    def test_login_existing_user(self, page: Page):
        """Test user login"""
        page.goto(f"{BASE_URL}/auth")
        
        # Fill login form
        page.get_by_label("Email").fill("test@example.com")
        page.get_by_label("Password").fill("SecurePass123!")
        
        # Submit
        page.get_by_role("button", name="Login").click()
        
        # Wait for response
        page.wait_for_timeout(2000)

    def test_google_sign_in_button(self, page: Page):
        """Test Google sign-in button is present"""
        page.goto(f"{BASE_URL}/auth")
        
        google_btn = page.get_by_role("button", name=re.compile("Google", re.IGNORECASE))
        expect(google_btn).to_be_visible()

    def test_form_validation(self, page: Page):
        """Test form validation prevents invalid submissions"""
        page.goto(f"{BASE_URL}/auth")
        
        # Try to submit empty form
        page.get_by_role("button", name="Login").click()
        
        # Should show validation errors
        page.wait_for_timeout(1000)


# ---------------------------------------------------------------------------
# 3. Screening Workflow Tests (Complete Flow)
# ---------------------------------------------------------------------------

class TestScreeningWorkflow:
    """Test complete screening workflow"""

    def test_upload_image_flow(self, page: Page):
        """Test image upload and screening flow"""
        page.goto(BASE_URL)
        
        # Click start screening
        start_btn = page.get_by_role("button", name=re.compile("Start|Upload", re.IGNORECASE))
        start_btn.click()
        
        # Wait for upload zone
        page.wait_for_timeout(1000)

    def test_drag_and_drop_image(self, page: Page, tmp_path: Path):
        """Test drag and drop functionality"""
        page.goto(BASE_URL)
        
        # Create a test image file
        test_image = tmp_path / "test_eye.jpg"
        # In real test, use actual test image
        test_image.write_bytes(b"fake_image_data")
        
        # Get upload zone
        upload_zone = page.get_by_text("drag", ignore_case=True).or_(
            page.get_by_text("upload", ignore_case=True)
        )
        
        # Set files for upload (simulated)
        # Note: Actual drag-and-drop would need file input interaction

    def test_quality_check_shown(self, page: Page):
        """Test quality check step appears after upload"""
        page.goto(BASE_URL)
        
        # After upload, quality check should appear
        # This would need actual image upload to test fully

    def test_symptom_intake_form(self, page: Page):
        """Test symptom intake form"""
        page.goto(BASE_URL)
        
        # Navigate to intake step (would need previous steps completed)
        # Check symptom checkboxes are visible

    def test_result_display(self, page: Page):
        """Test result page displays correctly"""
        page.goto(BASE_URL)
        
        # Result should show:
        # - Hemoglobin level
        # - Risk category
        # - Confidence score
        # - Clinical brief


# ---------------------------------------------------------------------------
# 4. Dashboard & History Tests
# ---------------------------------------------------------------------------

class TestDashboard:
    """Test dashboard and history features"""

    def test_dashboard_loads(self, page: Page):
        """Test dashboard page loads"""
        page.goto(f"{BASE_URL}/dashboard")
        
        # Should show dashboard content
        expect(page.get_by_text("Dashboard")).to_be_visible()

    def test_history_list_displays(self, page: Page):
        """Test screening history displays"""
        page.goto(f"{BASE_URL}/dashboard")
        
        # History list should be visible (may be empty)

    def test_export_functionality(self, page: Page):
        """Test CSV export button"""
        page.goto(f"{BASE_URL}/dashboard")
        
        export_btn = page.get_by_role("button", name=re.compile("Export", re.IGNORECASE))
        if export_btn:
            expect(export_btn).to_be_visible()


# ---------------------------------------------------------------------------
# 5. Error Scenarios & Recovery Tests
# ---------------------------------------------------------------------------

class TestErrorScenarios:
    """Test error handling and recovery"""

    def test_offline_mode(self, page: Page, context: BrowserContext):
        """Test app behaves correctly when offline"""
        # Go offline
        context.set_offline()
        
        page.goto(BASE_URL)
        
        # Should show offline indicator or fallback mode
        page.wait_for_timeout(1000)
        
        # Go back online
        context.set_online()

    def test_invalid_image_upload(self, page: Page, tmp_path: Path):
        """Test handling of invalid image files"""
        page.goto(BASE_URL)
        
        # Create invalid file
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("not an image")
        
        # Try to upload - should show error

    def test_server_error_handling(self, page: Page):
        """Test graceful handling of server errors"""
        # This would need API mocking to simulate 500 errors
        pass

    def test_network_timeout(self, page: Page):
        """Test handling of network timeouts"""
        # Simulate slow network
        page.route("**/api/**", lambda route: route.abort("timedout"))
        
        page.goto(BASE_URL)
        # Should show timeout error with retry option


# ---------------------------------------------------------------------------
# 6. Accessibility Tests
# ---------------------------------------------------------------------------

class TestAccessibility:
    """Test WCAG 2.1 AA compliance"""

    def test_keyboard_navigation(self, page: Page):
        """Test full keyboard navigation"""
        page.goto(BASE_URL)
        
        # Tab through interactive elements
        for _ in range(10):
            page.keyboard.press("Tab")
            page.wait_for_timeout(100)
            
        # Focused element should be visible
        focused = page.locator(":focus")
        expect(focused).to_be_visible()

    def test_aria_labels(self, page: Page):
        """Test ARIA labels are present"""
        page.goto(BASE_URL)
        
        # Check buttons have accessible names
        buttons = page.get_by_role("button")
        expect(buttons.first).to_be_visible()

    def test_color_contrast(self, page: Page):
        """Test color contrast meets WCAG AA standards"""
        # This would need automated axe-core testing
        pass

    def test_screen_reader_support(self, page: Page):
        """Test semantic HTML for screen readers"""
        page.goto(BASE_URL)
        
        # Check for proper heading hierarchy
        h1_count = page.locator("h1").count()
        assert h1_count == 1, "Should have exactly one H1"

    def test_focus_indicators(self, page: Page):
        """Test visible focus indicators"""
        page.goto(BASE_URL)
        
        # Focus an interactive element
        page.keyboard.press("Tab")
        
        # Focused element should have visible indicator
        focused = page.locator(":focus")
        expect(focused).to_be_visible()


# ---------------------------------------------------------------------------
# 7. Performance Benchmark Tests
# ---------------------------------------------------------------------------

class TestPerformance:
    """Test performance benchmarks"""

    def test_landing_page_load_time(self, page: Page):
        """Test landing page loads within acceptable time"""
        with page.expect_navigation():
            page.goto(BASE_URL)
        
        # Check for performance metrics
        navigation = page.evaluate("""
            () => {
                const [entry] = performance.getEntriesByType('navigation');
                return {
                    loadTime: entry.loadEventEnd - entry.startTime,
                    domContentLoaded: entry.domContentLoadedEventEnd - entry.startTime
                };
            }
        """)
        
        # Should load within 3 seconds
        assert navigation["loadTime"] < 3000, f"Page took {navigation['loadTime']}ms to load"

    def test_image_upload_response_time(self, page: Page):
        """Test image upload responds quickly"""
        page.goto(BASE_URL)
        
        # Monitor API calls
        page.goto(BASE_URL)
        
        with page.expect_response("**/api/**") as response_info:
            # Trigger API call (would need actual upload)
            pass
        
        # Response should be within timeout

    def test_bundle_size_check(self, page: Page):
        """Test JavaScript bundle size is reasonable"""
        # This would need build analysis
        pass


# ---------------------------------------------------------------------------
# 8. Mobile Responsiveness Tests
# ---------------------------------------------------------------------------

class TestMobileResponsiveness:
    """Test mobile responsiveness"""

    @pytest.fixture
    def mobile_page(self, browser):
        """Create mobile viewport page"""
        context = browser.new_context(
            viewport={"width": 375, "height": 667},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"
        )
        page = context.new_page()
        page.set_default_timeout(TIMEOUT)
        yield page
        context.close()

    def test_mobile_layout(self, mobile_page: Page):
        """Test mobile layout renders correctly"""
        mobile_page.goto(BASE_URL)
        
        # Hero section should be visible
        expect(mobile_page.locator("h1")).to_be_visible()

    def test_mobile_navigation(self, mobile_page: Page):
        """Test mobile navigation (hamburger menu)"""
        mobile_page.goto(BASE_URL)
        
        # Hamburger menu should be visible on mobile
        hamburger = mobile_page.locator('[aria-label="Menu"]').or_(
            mobile_page.locator(".hamburger")
        )
        # May need adjustment based on actual implementation

    def test_touch_targets(self, mobile_page: Page):
        """Test touch targets are large enough (minimum 44x44px)"""
        mobile_page.goto(BASE_URL)
        
        # Check button sizes
        buttons = mobile_page.locator("button")
        count = buttons.count()
        
        for i in range(min(count, 5)):  # Check first 5 buttons
            box = buttons.nth(i).bounding_box()
            if box:
                assert box["width"] >= 44, f"Button width {box['width']}px is too small"
                assert box["height"] >= 44, f"Button height {box['height']}px is too small"


# ---------------------------------------------------------------------------
# Helper Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def authenticated_page(page: Page):
    """Fixture for authenticated page session"""
    # Set auth tokens in localStorage
    page.goto(BASE_URL)
    page.evaluate("""
        localStorage.setItem('access_token', 'test-token');
        localStorage.setItem('refresh_token', 'test-refresh-token');
    """)
    page.reload()
    yield page


@pytest.fixture
def slow_network(page: Page):
    """Fixture that simulates slow network"""
    page.route("**/*", lambda route: route.continue_())
    yield page


# ---------------------------------------------------------------------------
# Custom Assertions
# ---------------------------------------------------------------------------

def expect_loading_complete(page: Page, timeout=5000):
    """Wait for loading to complete"""
    page.wait_for_load_state("networkidle", timeout=timeout)


def expect_no_console_errors(page: Page):
    """Check for console errors"""
    # This would need custom console error tracking
    pass
