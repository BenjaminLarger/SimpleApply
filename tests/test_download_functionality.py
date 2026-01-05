#!/usr/bin/env python3
"""
Test script to debug download functionality issues.
This will test PDF generation and file saving independently.
"""

import sys
import traceback
from pathlib import Path

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

def test_imports():
    """Test if all required imports work"""
    print("Testing imports...")
    try:
        from playwright.sync_api import sync_playwright
        print("✅ Playwright import successful")
    except ImportError as e:
        print(f"❌ Playwright import failed: {e}")
        return False

    try:
        import logging
        print("✅ Logging import successful")
    except ImportError as e:
        print(f"❌ Logging import failed: {e}")
        return False

    return True

def test_playwright_installation():
    """Test if Playwright browsers are installed"""
    print("\nTesting Playwright browser installation...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        print("✅ Playwright chromium browser works")
        return True
    except Exception as e:
        print(f"❌ Playwright browser test failed: {e}")
        print("Try running: playwright install chromium")
        return False

def test_pdf_generation():
    """Test PDF generation with sample HTML"""
    print("\nTesting PDF generation...")

    # Setup logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def convert_html_to_pdf(html_content: str) -> bytes:
        """Convert HTML content to PDF bytes using Playwright."""
        logger.info("Starting HTML to PDF conversion")
        try:
            from playwright.sync_api import sync_playwright
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
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            raise

    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Document</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <h1>Test PDF Generation</h1>
        <p>This is a test document to verify PDF generation is working.</p>
        <p>If you can see this in a PDF, the conversion is successful!</p>
    </body>
    </html>
    """

    try:
        pdf_bytes = convert_html_to_pdf(sample_html)
        print(f"✅ PDF generation successful - Generated {len(pdf_bytes)} bytes")
        return pdf_bytes
    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        traceback.print_exc()
        return None

def test_file_saving(pdf_bytes):
    """Test file saving functionality"""
    print("\nTesting file saving...")

    if not pdf_bytes:
        print("❌ Cannot test file saving - no PDF bytes provided")
        return False

    def save_file_to_applications(content: bytes, filename: str, file_type: str) -> str:
        """Save file to ~/Downloads/Applications/ directory and return the full path."""
        import logging
        logger = logging.getLogger(__name__)

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

    try:
        test_filename = "test_download.pdf"
        saved_path = save_file_to_applications(pdf_bytes, test_filename, "Test PDF")

        # Verify file exists and has correct size
        if Path(saved_path).exists():
            file_size = Path(saved_path).stat().st_size
            print(f"✅ File saving successful - Saved to {saved_path} ({file_size} bytes)")
            return True
        else:
            print(f"❌ File saving failed - File not found at {saved_path}")
            return False

    except Exception as e:
        print(f"❌ File saving failed: {e}")
        traceback.print_exc()
        return False

def test_directory_permissions():
    """Test if we can create directories and write files"""
    print("\nTesting directory permissions...")

    try:
        test_dir = Path.home() / "Downloads" / "Applications" / "test"
        test_dir.mkdir(parents=True, exist_ok=True)

        test_file = test_dir / "permission_test.txt"
        test_file.write_text("Permission test")

        if test_file.exists() and test_file.read_text() == "Permission test":
            print("✅ Directory and file permissions OK")
            # Clean up
            test_file.unlink()
            test_dir.rmdir()
            return True
        else:
            print("❌ File write/read verification failed")
            return False

    except Exception as e:
        print(f"❌ Directory/file permission test failed: {e}")
        return False

def test_template_loading():
    """Test if HTML templates can be loaded"""
    print("\nTesting template loading...")

    template_files = [
        "templates/cv_template.html",
        "templates/cover_letter_template.html"
    ]

    success = True
    for template_file in template_files:
        template_path = Path(template_file)
        if template_path.exists():
            try:
                content = template_path.read_text(encoding='utf-8')
                print(f"✅ {template_file} loaded successfully ({len(content)} chars)")
            except Exception as e:
                print(f"❌ Failed to read {template_file}: {e}")
                success = False
        else:
            print(f"❌ Template file not found: {template_file}")
            success = False

    return success

def main():
    """Run all tests"""
    print("🧪 Download Functionality Tester")
    print("=" * 50)

    results = {
        "imports": test_imports(),
        "playwright": test_playwright_installation(),
        "templates": test_template_loading(),
        "permissions": test_directory_permissions(),
    }

    # Only test PDF generation if basic requirements are met
    if results["imports"] and results["playwright"]:
        pdf_bytes = test_pdf_generation()
        results["pdf_generation"] = pdf_bytes is not None

        if results["pdf_generation"]:
            results["file_saving"] = test_file_saving(pdf_bytes)
        else:
            results["file_saving"] = False
    else:
        results["pdf_generation"] = False
        results["file_saving"] = False

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! Download functionality should work.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above for solutions.")
        print("\nCommon fixes:")
        print("- Install Playwright browsers: playwright install chromium")
        print("- Check file permissions in ~/Downloads/")
        print("- Ensure templates directory exists with required files")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)