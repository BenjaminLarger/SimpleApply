#!/usr/bin/env python3
"""
Streamlit UI for AI-Powered Job Application System
"""

import streamlit as st
import os
import yaml
import logging
from playwright.sync_api import sync_playwright

from src.job_parser import parse_job_offer
from src.skills_matcher import match_skills
from src.project_selector import select_projects
from src.template_processor import create_template_processor
from src.models import UserProfile
from src.cost_tracker import get_cost_tracker, reset_cost_tracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


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


def process_job_application(job_offer_text: str, user_profile: UserProfile) -> tuple[str, str, object, object]:
    """Process job application and return CV, cover letter HTML, job offer data, and matched skills."""
    logger.info("Starting job application processing")

    # Parse job offer
    logger.info("Parsing job offer text")
    job_offer = parse_job_offer(job_offer_text)
    logger.info(f"Parsed job offer for {job_offer.company_name} - {job_offer.job_title}")

    # Match skills
    logger.info("Matching user skills with job requirements")
    matched_skills = match_skills(job_offer, user_profile)
    logger.info(f"Found {len(matched_skills.matched_skills)} matching skills")

    # Select projects
    logger.info("Selecting most relevant projects")
    selected_projects = select_projects(job_offer, user_profile.projects)
    logger.info(f"Selected {selected_projects} projects")

    # Generate documents
    logger.info("Generating CV and cover letter templates")
    template_processor = create_template_processor()
    generated_content = template_processor.process_templates(
        job_offer=job_offer,
        user_profile=user_profile,
        matched_skills=matched_skills,
        selected_projects=selected_projects
    )
    logger.info("Document generation completed successfully")

    return generated_content.cv_html, generated_content.cover_letter_html, job_offer, matched_skills


def main():
    logger.info("Starting Streamlit application")
    st.set_page_config(
        page_title="AI Job Application Generator",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🚀 AI-Powered Job Application System")
    st.markdown("Generate tailored CVs and cover letters by analyzing job offers")

    # Cost tracking reset option
    col_title, col_reset = st.columns([4, 1])
    with col_reset:
        if st.button("🔄 Reset Costs", help="Reset API cost tracking for this session"):
            reset_cost_tracker()
            st.success("✅ Cost tracking reset!")

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

    # Sidebar cost display
    st.sidebar.header("💰 Session Costs")
    cost_tracker = get_cost_tracker()
    if cost_tracker.total_calls > 0:
        st.sidebar.metric(
            label="Total Cost",
            value=f"${cost_tracker.total_cost:.4f}",
            help="Total API costs for this session"
        )
        st.sidebar.metric(
            label="API Calls",
            value=cost_tracker.total_calls,
            help="Total API calls made"
        )
        st.sidebar.metric(
            label="Tokens Used",
            value=f"{cost_tracker.total_tokens:,}",
            help="Total tokens consumed"
        )
    else:
        st.sidebar.write("No API calls made yet")

    # Generate button
    if st.button("🚀 Generate CV & Cover Letter", type="primary", use_container_width=True):
        if not job_offer_text.strip():
            st.error("Please enter a job offer description")
            st.stop()

        try:
            with st.spinner("🔍 Analyzing job offer and generating documents..."):
                cv_html, cover_letter_html, job_offer, matched_skills = process_job_application(job_offer_text, user_profile)

            st.success("✅ Documents generated successfully!")

            # Display cost information
            cost_tracker = get_cost_tracker()
            if cost_tracker.total_calls > 0:
                with st.expander("💰 API Cost Summary", expanded=False):
                    col_cost1, col_cost2 = st.columns(2)

                    with col_cost1:
                        st.metric(
                            label="Total Cost",
                            value=f"${cost_tracker.total_cost:.4f} USD",
                            help="Total cost of OpenAI API calls for this generation"
                        )
                        st.metric(
                            label="Total Tokens",
                            value=f"{cost_tracker.total_tokens:,}",
                            help="Total tokens used across all API calls"
                        )

                    with col_cost2:
                        st.metric(
                            label="API Calls",
                            value=cost_tracker.total_calls,
                            help="Number of API calls made"
                        )

                        # Show cost breakdown
                        summary = cost_tracker.get_summary()
                        if summary["operations"]:
                            st.write("**Cost by Operation:**")
                            for op, stats in summary["operations"].items():
                                st.write(f"• {op}: ${stats['cost']:.4f}")

            # Display job analysis results
            st.header("🔍 Job Analysis Results")

            col_job, col_skills = st.columns(2)

            with col_job:
                st.subheader("📋 Job Requirements")
                st.write(f"**Position:** {job_offer.job_title}")
                st.write(f"**Company:** {job_offer.company_name}")
                st.write(f"**Location:** {job_offer.location}")

                st.write("**Required Skills:**")
                for skill in job_offer.skills_required:
                    st.write(f"• {skill}")

            with col_skills:
                st.subheader("🎯 Skills Matching")
                st.write(f"**Match Rate:** {len(matched_skills.matched_skills)}/{len(job_offer.skills_required)} ({len(matched_skills.matched_skills)/len(job_offer.skills_required)*100:.1f}%)")

                st.write("**Matched Skills:**")
                for skill in matched_skills.matched_skills:
                    st.write(f"✅ {skill}")

                if len(matched_skills.matched_skills) < len(job_offer.skills_required):
                    missing_skills = set(job_offer.skills_required) - set(matched_skills.matched_skills)
                    st.write("**Skills to Highlight:**")
                    for skill in missing_skills:
                        st.write(f"⚠️ {skill}")

            # Create download section
            st.header("📥 Download Documents")

            # Generate clean filenames
            company_clean = "".join(c for c in job_offer.company_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            position_clean = "".join(c for c in job_offer.job_title if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')

            cv_pdf_name = f"cv_{company_clean}_{position_clean}.pdf"
            cv_html_name = f"cv_{company_clean}_{position_clean}.html"
            cl_pdf_name = f"cover_letter_{company_clean}_{position_clean}.pdf"
            cl_html_name = f"cover_letter_{company_clean}_{position_clean}.html"

            col_cv, col_cl = st.columns(2)

            with col_cv:
                st.subheader("📋 CV")

                # Convert to PDF
                cv_pdf = convert_html_to_pdf(cv_html)

                st.download_button(
                    label="📄 Download CV (PDF)",
                    data=cv_pdf,
                    file_name=cv_pdf_name,
                    mime="application/pdf",
                    use_container_width=True
                )

                st.download_button(
                    label="🌐 Download CV (HTML)",
                    data=cv_html,
                    file_name=cv_html_name,
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
                    file_name=cl_pdf_name,
                    mime="application/pdf",
                    use_container_width=True
                )

                st.download_button(
                    label="🌐 Download Cover Letter (HTML)",
                    data=cover_letter_html,
                    file_name=cl_html_name,
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
    print("🚀 Starting AI Job Application System...")
    logger.info("Application started")
    main()