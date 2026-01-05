#!/usr/bin/env python3
"""
Test script that mimics the exact Streamlit workflow to identify where the issue occurs.
"""

import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

def test_streamlit_workflow():
    """Test the exact workflow that happens in Streamlit"""
    print("🧪 Testing Streamlit-like workflow...")

    # Import required modules
    from playwright.sync_api import sync_playwright
    import logging

    # Setup logging like in Streamlit app
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Copy exact functions from streamlit_app.py
    def convert_html_to_pdf(html_content: str) -> bytes:
        """Convert HTML content to PDF bytes using Playwright."""
        logger.info("Starting HTML to PDF conversion")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_content)
            pdf_bytes = page.pdf(
                format='A4',
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'},
                print_background=True
            )
            browser.close()
            logger.info("PDF conversion completed successfully")
            return pdf_bytes

    def save_file_to_applications(content: bytes, filename: str, file_type: str) -> str:
        """Save file to ~/Downloads/Applications/ directory and return the full path."""
        # Create the directory path
        downloads_path = Path.home() / "Downloads" / "Applications"
        downloads_path.mkdir(parents=True, exist_ok=True)

        # Create full file path
        file_path = downloads_path / filename

        # Write the file
        with open(file_path, 'wb') as f:
            f.write(content)

        logger.info(f"Saved {file_type} to {file_path}")
        return str(file_path)

    # Step 1: Simulate getting HTML content (like from process_job_application)
    print("Step 1: Creating sample HTML content...")

    cv_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CV - Test User</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            .section { margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>Test User</h1>
        <div class="section">
            <h2>Experience</h2>
            <p>Senior Software Developer at TestCorp</p>
        </div>
        <div class="section">
            <h2>Skills</h2>
            <p>Python, JavaScript, React</p>
        </div>
    </body>
    </html>
    """

    cover_letter_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cover Letter - Test Position</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <h1>Cover Letter</h1>
        <p>Dear Hiring Manager,</p>
        <p>I am writing to express my interest in the Test Position at your company.</p>
        <p>Best regards,<br>Test User</p>
    </body>
    </html>
    """

    print(f"✅ CV HTML created ({len(cv_html)} chars)")
    print(f"✅ Cover Letter HTML created ({len(cover_letter_html)} chars)")

    # Step 2: Generate filenames (like in Streamlit app)
    print("\nStep 2: Generating filenames...")

    company_clean = "TestCorp"
    position_clean = "Senior_Developer"

    cv_pdf_name = f"CV_{company_clean}_{position_clean}.pdf"
    cv_html_name = f"CV_{company_clean}_{position_clean}.html"
    cl_pdf_name = f"Cover_Letter_{company_clean}_{position_clean}.pdf"
    cl_html_name = f"Cover_Letter_{company_clean}_{position_clean}.html"

    print(f"✅ CV PDF name: {cv_pdf_name}")
    print(f"✅ CL PDF name: {cl_pdf_name}")

    # Step 3: Convert to PDF (like in Streamlit app - outside columns)
    print("\nStep 3: Converting HTML to PDF...")

    try:
        cv_pdf = convert_html_to_pdf(cv_html)
        print(f"✅ CV PDF conversion successful ({len(cv_pdf)} bytes)")
    except Exception as e:
        print(f"❌ CV PDF conversion failed: {e}")
        return False

    try:
        cl_pdf = convert_html_to_pdf(cover_letter_html)
        print(f"✅ CL PDF conversion successful ({len(cl_pdf)} bytes)")
    except Exception as e:
        print(f"❌ CL PDF conversion failed: {e}")
        return False

    # Step 4: Test individual downloads (like individual buttons)
    print("\nStep 4: Testing individual downloads...")

    try:
        cv_saved_path = save_file_to_applications(cv_pdf, cv_pdf_name, "CV PDF")
        print(f"✅ CV PDF saved: {cv_saved_path}")
    except Exception as e:
        print(f"❌ CV PDF save failed: {e}")
        return False

    try:
        cl_saved_path = save_file_to_applications(cl_pdf, cl_pdf_name, "Cover Letter PDF")
        print(f"✅ CL PDF saved: {cl_saved_path}")
    except Exception as e:
        print(f"❌ CL PDF save failed: {e}")
        return False

    # Step 5: Test combined download (like combined button)
    print("\nStep 5: Testing combined download (simulating button click)...")

    try:
        # This simulates exactly what the combined button does
        cv_saved_path_combined = save_file_to_applications(cv_pdf, f"Combined_{cv_pdf_name}", "CV PDF")
        cl_saved_path_combined = save_file_to_applications(cl_pdf, f"Combined_{cl_pdf_name}", "Cover Letter PDF")

        print(f"✅ Combined CV PDF saved: {cv_saved_path_combined}")
        print(f"✅ Combined CL PDF saved: {cl_saved_path_combined}")

        # Check if files actually exist and have content
        if Path(cv_saved_path_combined).exists() and Path(cl_saved_path_combined).exists():
            cv_size = Path(cv_saved_path_combined).stat().st_size
            cl_size = Path(cl_saved_path_combined).stat().st_size

            if cv_size > 0 and cl_size > 0:
                print(f"✅ Combined download verification successful")
                print(f"   CV file size: {cv_size} bytes")
                print(f"   CL file size: {cl_size} bytes")
                return True
            else:
                print(f"❌ Combined download files are empty")
                return False
        else:
            print(f"❌ Combined download files do not exist")
            return False

    except Exception as e:
        print(f"❌ Combined download failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_variable_scope():
    """Test if variable scope could be an issue"""
    print("\n🔍 Testing variable scope simulation...")

    # Simulate Streamlit's button logic and variable scope
    cv_html = "<html><body>CV Content</body></html>"
    cover_letter_html = "<html><body>Cover Letter Content</body></html>"

    # Simulate the PDF generation outside columns (as in fixed code)
    print("Variables created in outer scope...")
    cv_pdf = b"fake_cv_pdf_bytes"
    cl_pdf = b"fake_cl_pdf_bytes"

    # Simulate column context
    print("Testing access from simulated 'column' context...")
    try:
        # This simulates accessing variables from button callback
        test_cv = cv_pdf
        test_cl = cl_pdf
        print(f"✅ Variables accessible: CV={len(test_cv)} bytes, CL={len(test_cl)} bytes")
        return True
    except NameError as e:
        print(f"❌ Variable scope issue: {e}")
        return False

def main():
    """Run all workflow tests"""
    print("🧪 Streamlit Workflow Tester")
    print("=" * 60)

    # Test 1: Variable scope
    scope_test = test_variable_scope()

    # Test 2: Full workflow
    workflow_test = test_streamlit_workflow()

    # Summary
    print("\n" + "=" * 60)
    print("📊 WORKFLOW TEST RESULTS")
    print("=" * 60)

    print(f"Variable Scope Test: {'✅ PASS' if scope_test else '❌ FAIL'}")
    print(f"Full Workflow Test: {'✅ PASS' if workflow_test else '❌ FAIL'}")

    if scope_test and workflow_test:
        print("\n🎉 All workflow tests passed!")
        print("The issue might be specific to Streamlit's execution environment.")
        print("\nSuggestions:")
        print("1. Check Streamlit logs for specific error messages")
        print("2. Add debug prints in the actual Streamlit app")
        print("3. Verify Streamlit session state isn't interfering")
    else:
        print("\n⚠️  Workflow tests failed. Check errors above.")

    return scope_test and workflow_test

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)