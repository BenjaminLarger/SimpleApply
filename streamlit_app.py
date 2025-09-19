#!/usr/bin/env python3
"""
Streamlit UI for AI-Powered Job Application System
"""

import streamlit as st
import tempfile
import os
import yaml
from pathlib import Path
from io import BytesIO
from playwright.sync_api import sync_playwright

from src.job_parser import parse_job_offer
from src.skills_matcher import match_skills
from src.project_selector import select_projects
from src.template_processor import create_template_processor
from src.models import UserProfile


def convert_html_to_pdf(html_content: str) -> bytes:
    """Convert HTML content to PDF bytes using Playwright."""
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
        return pdf_bytes


def process_job_application(job_offer_text: str, user_profile: UserProfile) -> tuple[str, str]:
    """Process job application and return CV and cover letter HTML."""
    # Parse job offer
    job_offer = parse_job_offer(job_offer_text)

    # Match skills
    matched_skills = match_skills(job_offer, user_profile)

    # Select projects
    selected_projects = select_projects(job_offer, user_profile.projects)

    # Generate documents
    template_processor = create_template_processor()
    generated_content = template_processor.process_templates(
        job_offer=job_offer,
        user_profile=user_profile,
        matched_skills=matched_skills,
        selected_projects=selected_projects
    )

    return generated_content.cv_html, generated_content.cover_letter_html


def main():
    st.set_page_config(
        page_title="AI Job Application Generator",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🚀 AI-Powered Job Application System")
    st.markdown("Generate tailored CVs and cover letters by analyzing job offers")

    # Sidebar for user profile
    st.sidebar.header("👤 User Profile")

    # Check if default profile exists
    default_profile_path = "templates/user_profile.yaml"

    if os.path.exists(default_profile_path):
        use_default = st.sidebar.checkbox("Use default profile", value=True)
        if use_default:
            with open(default_profile_path, 'r', encoding='utf-8') as f:
                profile_data = yaml.safe_load(f)
            user_profile = UserProfile(**profile_data)
            st.sidebar.success(f"✅ Using profile for {user_profile.personal_info.name}")
        else:
            uploaded_profile = st.sidebar.file_uploader(
                "Upload your profile (YAML)",
                type=['yaml', 'yml'],
                help="Upload a YAML file with your profile information"
            )
            if uploaded_profile:
                profile_data = yaml.safe_load(uploaded_profile)
                user_profile = UserProfile(**profile_data)
                st.sidebar.success(f"✅ Profile loaded for {user_profile.personal_info.name}")
            else:
                st.sidebar.warning("Please upload a profile file")
                st.stop()
    else:
        uploaded_profile = st.sidebar.file_uploader(
            "Upload your profile (YAML)",
            type=['yaml', 'yml'],
            help="Upload a YAML file with your profile information"
        )
        if uploaded_profile:
            profile_data = yaml.safe_load(uploaded_profile)
            user_profile = UserProfile(**profile_data)
            st.sidebar.success(f"✅ Profile loaded for {user_profile.personal_info.name}")
        else:
            st.sidebar.warning("Please upload a profile file")
            st.stop()

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📄 Job Offer Input")
        job_offer_text = st.text_area(
            "Paste the job offer text here:",
            height=400,
            placeholder="Paste the complete job offer description, requirements, and any other relevant information..."
        )

        # Optional file upload for job offer
        uploaded_job_file = st.file_uploader(
            "Or upload a job offer file",
            type=['txt', 'md'],
            help="Upload a text file containing the job offer"
        )

        if uploaded_job_file:
            job_offer_text = uploaded_job_file.read().decode('utf-8')
            st.success("✅ Job offer loaded from file")

    with col2:
        st.header("🎯 Profile Summary")
        if 'user_profile' in locals():
            st.write(f"**Name:** {user_profile.personal_info.name}")
            st.write(f"**Email:** {user_profile.personal_info.email}")
            st.write(f"**Skills:** {len(user_profile.skills)} total")
            st.write(f"**Projects:** {len(user_profile.projects)} available")
            st.write(f"**Experiences:** {len(user_profile.experiences)} entries")
            st.write(f"**Languages:** {', '.join(user_profile.languages)}")

    # Generate button
    if st.button("🚀 Generate CV & Cover Letter", type="primary", use_container_width=True):
        if not job_offer_text.strip():
            st.error("Please enter a job offer description")
            st.stop()

        try:
            with st.spinner("🔍 Analyzing job offer and generating documents..."):
                cv_html, cover_letter_html = process_job_application(job_offer_text, user_profile)

            st.success("✅ Documents generated successfully!")

            # Create download section
            st.header("📥 Download Documents")

            col_cv, col_cl = st.columns(2)

            with col_cv:
                st.subheader("📋 CV")

                # Convert to PDF
                cv_pdf = convert_html_to_pdf(cv_html)

                st.download_button(
                    label="📄 Download CV (PDF)",
                    data=cv_pdf,
                    file_name="CV.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

                st.download_button(
                    label="🌐 Download CV (HTML)",
                    data=cv_html,
                    file_name="CV.html",
                    mime="text/html",
                    use_container_width=True
                )

            with col_cl:
                st.subheader("💌 Cover Letter")

                # Convert to PDF
                cl_pdf = convert_html_to_pdf(cover_letter_html)

                st.download_button(
                    label="📄 Download Cover Letter (PDF)",
                    data=cl_pdf,
                    file_name="Cover_Letter.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

                st.download_button(
                    label="🌐 Download Cover Letter (HTML)",
                    data=cover_letter_html,
                    file_name="Cover_Letter.html",
                    mime="text/html",
                    use_container_width=True
                )

            # Preview section
            with st.expander("👀 Preview CV"):
                st.components.v1.html(cv_html, height=600, scrolling=True)

            with st.expander("👀 Preview Cover Letter"):
                st.components.v1.html(cover_letter_html, height=600, scrolling=True)

        except Exception as e:
            st.error(f"❌ Error generating documents: {str(e)}")
            st.exception(e)


if __name__ == "__main__":
    main()