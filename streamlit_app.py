#!/usr/bin/env python3
"""
Streamlit UI for AI-Powered Job Application System
"""

import streamlit as st
import os
import yaml
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright
from pathlib import Path

from src.job_parser import parse_job_offer
from src.skills_matcher import match_skills
from src.project_selector import select_projects
from src.template_processor import create_template_processor
from src.models import UserProfile
from src.cost_tracker import get_cost_tracker, reset_cost_tracker
from src.database import ApplicationDatabase, Application

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


def save_file_to_applications(content: bytes, filename: str, file_type: str) -> str:
    """Save file to ~/Downloads/Applications/ directory organized by type and return the full path."""
    # Create the base directory path
    base_path = Path.home() / "Downloads" / "Applications"

    # Determine subdirectory based on file type
    if "CV" in file_type:
        downloads_path = base_path / "CVs"
    elif "Cover Letter" in file_type:
        downloads_path = base_path / "CoverLetters"
    else:
        downloads_path = base_path

    downloads_path.mkdir(parents=True, exist_ok=True)

    # Create full file path
    file_path = downloads_path / filename

    # Write the file
    with open(file_path, 'wb') as f:
        f.write(content)

    logger.info(f"Saved {file_type} to {file_path}")
    return str(file_path)


def process_job_application(job_offer_text: str, user_profile: UserProfile) -> tuple[str, str, object, object, int]:
    """Process job application and return CV, cover letter HTML, job offer data, matched skills, and application ID."""
    logger.info("Starting job application processing")

    # Initialize database
    db = ApplicationDatabase()

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

    # Calculate application cost and matching rate
    cost_tracker = get_cost_tracker()
    application_cost = cost_tracker.total_cost
    total_skills = len(job_offer.skills_required)
    matched_count = len(matched_skills.matched_skills)
    matching_rate = (matched_count / total_skills) if total_skills > 0 else 0.0

    # Get unmatched skills
    unmatched_skills = list(set(job_offer.skills_required) - set(matched_skills.matched_skills))

    # Save application to database
    application = Application(
        company=job_offer.company_name,
        position=job_offer.job_title,
        matching_rate=matching_rate,
        unmatched_skills=unmatched_skills,
        matched_skills=matched_skills.matched_skills,
        location=job_offer.location,
        job_offer_input=job_offer_text,
        application_cost=application_cost
    )

    application_id = db.save_application(application)
    logger.info(f"Application saved to database with ID: {application_id}")

    return generated_content.cv_html, generated_content.cover_letter_html, job_offer, matched_skills, application_id


def show_follow_up_page():
    """Display the application follow-up page"""
    st.title("📊 Application Follow-Up Dashboard")
    st.markdown("Track and manage your job applications")

    db = ApplicationDatabase()
    applications = db.get_all_applications()

    if not applications:
        st.info("No applications found. Generate your first application on the main page!")
        return

    # Summary metrics
    total_cost = db.get_total_cost()
    avg_match_rate = sum(app.matching_rate for app in applications) / len(applications)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Applications", len(applications))
    with col2:
        st.metric("Total Cost", f"${total_cost:.4f}")
    with col3:
        st.metric("Avg Match Rate", f"{avg_match_rate:.1%}")
    with col4:
        st.metric("This Month", len([app for app in applications if app.created_at.month == datetime.now().month]))

    # Filters
    st.header("🔍 Filter Applications")
    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        company_filter = st.selectbox(
            "Filter by Company",
            ["All"] + sorted(list(set(app.company for app in applications))),
            key="company_filter"
        )

    with col_filter2:
        min_match_rate = st.slider(
            "Minimum Match Rate",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1
        )

    with col_filter3:
        sort_by = st.selectbox(
            "Sort by",
            ["Date (Newest)", "Date (Oldest)", "Match Rate (High)", "Match Rate (Low)", "Cost (High)", "Cost (Low)"]
        )

    # Apply filters
    filtered_apps = applications
    if company_filter != "All":
        filtered_apps = [app for app in filtered_apps if app.company == company_filter]

    filtered_apps = [app for app in filtered_apps if app.matching_rate >= min_match_rate]

    # Apply sorting
    if sort_by == "Date (Newest)":
        filtered_apps.sort(key=lambda x: x.created_at, reverse=True)
    elif sort_by == "Date (Oldest)":
        filtered_apps.sort(key=lambda x: x.created_at)
    elif sort_by == "Match Rate (High)":
        filtered_apps.sort(key=lambda x: x.matching_rate, reverse=True)
    elif sort_by == "Match Rate (Low)":
        filtered_apps.sort(key=lambda x: x.matching_rate)
    elif sort_by == "Cost (High)":
        filtered_apps.sort(key=lambda x: x.application_cost, reverse=True)
    elif sort_by == "Cost (Low)":
        filtered_apps.sort(key=lambda x: x.application_cost)

    st.header(f"📋 Applications ({len(filtered_apps)} found)")

    # Applications table
    if filtered_apps:
        for app in filtered_apps:
            with st.expander(f"{app.company} - {app.position} ({app.matching_rate:.0%} match)", expanded=False):
                col_info, col_actions = st.columns([3, 1])

                with col_info:
                    st.write(f"**Company:** {app.company}")
                    st.write(f"**Position:** {app.position}")
                    st.write(f"**Location:** {app.location}")
                    st.write(f"**Applied:** {app.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**Match Rate:** {app.matching_rate:.1%}")
                    st.write(f"**Cost:** ${app.application_cost:.4f}")

                    st.write("**Matched Skills:**")
                    if app.matched_skills:
                        for skill in app.matched_skills:
                            st.write(f"✅ {skill}")
                    else:
                        st.write("None")

                    if app.unmatched_skills:
                        st.write("**Skills to Develop:**")
                        for skill in app.unmatched_skills:
                            st.write(f"⚠️ {skill}")

                with col_actions:
                    st.write("**Actions:**")

                    if st.button(f"📄 View Job Offer", key=f"view_{app.id}"):
                        st.text_area(
                            "Original Job Offer:",
                            value=app.job_offer_input,
                            height=200,
                            key=f"job_offer_{app.id}"
                        )

                    if st.button(f"🗑️ Delete", key=f"delete_{app.id}", type="secondary"):
                        if db.delete_application(app.id):
                            st.success("Application deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete application")

    # Analytics section
    if len(applications) >= 3:  # Only show analytics if we have enough data
        st.header("📈 Analytics")

        # Match rate trend
        apps_by_date = sorted(applications, key=lambda x: x.created_at)
        dates = [app.created_at.date() for app in apps_by_date]
        match_rates = [app.matching_rate for app in apps_by_date]

        try:
            import plotly.express as px
            import pandas as pd
        except ImportError:
            st.error("Plotly and pandas are required for analytics. Install with: pip install plotly pandas")
            return

        df = pd.DataFrame({
            'Date': dates,
            'Match Rate': [rate * 100 for rate in match_rates],
            'Company': [app.company for app in apps_by_date]
        })

        fig = px.line(df, x='Date', y='Match Rate',
                     title='Match Rate Trend Over Time',
                     labels={'Match Rate': 'Match Rate (%)'})
        st.plotly_chart(fig, use_container_width=True)

        # Company comparison
        company_stats = {}
        for app in applications:
            if app.company not in company_stats:
                company_stats[app.company] = {'count': 0, 'avg_match': 0, 'total_cost': 0}
            company_stats[app.company]['count'] += 1
            company_stats[app.company]['avg_match'] += app.matching_rate
            company_stats[app.company]['total_cost'] += app.application_cost

        for company in company_stats:
            company_stats[company]['avg_match'] /= company_stats[company]['count']

        company_df = pd.DataFrame([
            {
                'Company': company,
                'Applications': stats['count'],
                'Avg Match Rate': stats['avg_match'] * 100,
                'Total Cost': stats['total_cost']
            }
            for company, stats in company_stats.items()
        ])

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            # Company applications chart
            fig_company = px.bar(company_df, x='Company', y='Applications',
                               title='Applications by Company',
                               labels={'Applications': 'Number of Applications'})
            st.plotly_chart(fig_company, use_container_width=True)

        with col_chart2:
            # Average match rate by company
            fig_match = px.bar(company_df, x='Company', y='Avg Match Rate',
                             title='Average Match Rate by Company',
                             labels={'Avg Match Rate': 'Average Match Rate (%)'})
            st.plotly_chart(fig_match, use_container_width=True)

        # Most unmatched skills indicator
        st.subheader("⚠️ Most Unmatched Skills Across Applications")

        # Aggregate all unmatched skills
        unmatched_skills_counter = {}
        for app in applications:
            for skill in app.unmatched_skills:
                unmatched_skills_counter[skill] = unmatched_skills_counter.get(skill, 0) + 1

        if unmatched_skills_counter:
            # Sort by frequency (most common first)
            sorted_unmatched = sorted(unmatched_skills_counter.items(), key=lambda x: x[1], reverse=True)

            # Create DataFrame for visualization
            unmatched_df = pd.DataFrame(sorted_unmatched[:10], columns=['Skill', 'Frequency'])

            col_unmatched1, col_unmatched2 = st.columns([2, 1])

            with col_unmatched1:
                # Bar chart of most unmatched skills
                fig_unmatched = px.bar(unmatched_df, x='Skill', y='Frequency',
                                     title='Top 10 Most Unmatched Skills',
                                     labels={'Frequency': 'Number of Applications Missing This Skill'})
                fig_unmatched.update_xaxes(tickangle=45)
                st.plotly_chart(fig_unmatched, use_container_width=True)

            with col_unmatched2:
                st.write("**Skills Development Priority:**")
                for i, (skill, count) in enumerate(sorted_unmatched[:5], 1):
                    percentage = (count / len(applications)) * 100
                    st.write(f"{i}. **{skill}** - Missing in {count}/{len(applications)} applications ({percentage:.1f}%)")

                if len(sorted_unmatched) > 5:
                    with st.expander("View more unmatched skills"):
                        for i, (skill, count) in enumerate(sorted_unmatched[5:15], 6):
                            percentage = (count / len(applications)) * 100
                            st.write(f"{i}. {skill} - {count} applications ({percentage:.1f}%)")
        else:
            st.info("No unmatched skills data available.")

        # Skills improvement insights
        if unmatched_skills_counter:
            st.subheader("💡 Skills Development Insights")
            total_apps = len(applications)
            most_missed = sorted_unmatched[0] if sorted_unmatched else None

            if most_missed:
                skill_name, miss_count = most_missed
                miss_percentage = (miss_count / total_apps) * 100

                col_insight1, col_insight2 = st.columns(2)

                with col_insight1:
                    st.metric(
                        label="Most Missed Skill",
                        value=skill_name,
                        delta=f"Missing in {miss_percentage:.1f}% of applications"
                    )

                with col_insight2:
                    # Calculate potential improvement in match rate
                    if miss_count > 0:
                        avg_improvement = miss_count / total_apps * 100
                        st.metric(
                            label="Potential Match Rate Improvement",
                            value=f"+{avg_improvement:.1f}%",
                            delta="If this skill is acquired"
                        )


def main():
    logger.info("Starting Streamlit application")
    st.set_page_config(
        page_title="AI Job Application Generator",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Page navigation
    page = st.sidebar.selectbox(
        "Navigate",
        ["🚀 Generate Application", "📊 Follow-Up Dashboard"]
    )

    if page == "📊 Follow-Up Dashboard":
        show_follow_up_page()
        return

    st.title("🚀 AI-Powered Job Application System")
    st.markdown("Generate tailored CVs and cover letters by analyzing job offers")

    # Cost tracking reset option
    _, col_reset = st.columns([4, 1])
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

    # Applications history
    st.sidebar.header("📊 Applications History")
    db = ApplicationDatabase()
    applications = db.get_all_applications()

    if applications:
        total_cost = db.get_total_cost()
        st.sidebar.metric(
            label="Total Applications",
            value=len(applications),
            help="Total number of applications created"
        )
        st.sidebar.metric(
            label="Total Cost (All Time)",
            value=f"${total_cost:.4f}",
            help="Total cost of all applications"
        )

        with st.sidebar.expander("🔍 View Applications", expanded=False):
            for app in applications[:5]:  # Show last 5 applications
                st.write(f"**{app.company}** - {app.position}")
                st.write(f"Match: {app.matching_rate:.1%} | Cost: ${app.application_cost:.4f}")
                st.write(f"Date: {app.created_at.strftime('%Y-%m-%d %H:%M')}")
                st.write("---")

            if len(applications) > 5:
                st.write(f"... and {len(applications) - 5} more applications")
    else:
        st.sidebar.write("No applications yet")

    # Generate button
    if st.button("🚀 Generate CV & Cover Letter", type="primary", use_container_width=True):
        if not job_offer_text.strip():
            st.error("Please enter a job offer description")
            st.stop()

        try:
            with st.spinner("🔍 Analyzing job offer and generating documents..."):
                cv_html, cover_letter_html, job_offer, matched_skills, application_id = process_job_application(job_offer_text, user_profile)

            # Store in session state for persistence across reruns
            st.session_state.cv_html = cv_html
            st.session_state.cover_letter_html = cover_letter_html
            st.session_state.job_offer = job_offer
            st.session_state.matched_skills = matched_skills
            st.session_state.application_id = application_id

            st.success(f"✅ Documents generated successfully! Application saved with ID: {application_id}")

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
                total_required = len(job_offer.skills_required)
                matched_count = len(matched_skills.matched_skills)
                match_percentage = (matched_count / total_required * 100) if total_required > 0 else 0.0
                st.write(f"**Match Rate:** {matched_count}/{total_required} ({match_percentage:.1f}%)")

                st.write("**Matched Skills:**")
                for skill in matched_skills.matched_skills:
                    st.write(f"✅ {skill}")

                if len(matched_skills.matched_skills) < len(job_offer.skills_required):
                    missing_skills = set(job_offer.skills_required) - set(matched_skills.matched_skills)
                    st.write("**Skills to Highlight:**")
                    for skill in missing_skills:
                        st.write(f"⚠️ {skill}")

        except Exception as e:
            st.error(f"❌ Error generating documents: {str(e)}")
            st.exception(e)

    # Download section - available if documents exist in session state
    if hasattr(st.session_state, 'cv_html') and hasattr(st.session_state, 'cover_letter_html'):
        st.header("📥 Download Documents")

        # Get data from session state
        cv_html = st.session_state.cv_html
        cover_letter_html = st.session_state.cover_letter_html
        job_offer = st.session_state.job_offer
        matched_skills = st.session_state.matched_skills

        # Generate clean filenames
        company_clean = "".join(c for c in job_offer.company_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        position_clean = "".join(c for c in job_offer.job_title if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')

        cv_pdf_name = f"CV_{company_clean}_{position_clean}.pdf"
        cv_html_name = f"CV_{company_clean}_{position_clean}.html"
        cl_pdf_name = f"Cover_Letter_{company_clean}_{position_clean}.pdf"
        cl_html_name = f"Cover_Letter_{company_clean}_{position_clean}.html"

        col_cv, col_cl = st.columns(2)

        with col_cv:
            st.subheader("📋 CV")

            if st.button("📄 Download CV (PDF)", key="cv_pdf_btn", use_container_width=True):
                logger.info("CV PDF download button clicked")
                try:
                    cv_pdf = convert_html_to_pdf(cv_html)
                    saved_path = save_file_to_applications(cv_pdf, cv_pdf_name, "CV PDF")
                    logger.info(f"CV PDF saved to: {saved_path}")
                    st.success(f"✅ CV PDF saved to: {saved_path}")
                except Exception as e:
                    logger.error(f"Error saving CV PDF: {str(e)}")
                    st.error(f"❌ Error saving CV PDF: {str(e)}")

            if st.button("🌐 Download CV (HTML)", key="cv_html_btn", use_container_width=True):
                try:
                    saved_path = save_file_to_applications(cv_html.encode('utf-8'), cv_html_name, "CV HTML")
                    logger.info(f"CV HTML saved to: {saved_path}")
                    st.success(f"✅ CV HTML saved to: {saved_path}")
                except Exception as e:
                    logger.error(f"Error saving CV HTML: {str(e)}")
                    st.error(f"❌ Error saving CV HTML: {str(e)}")

        with col_cl:
            st.subheader("💌 Cover Letter")

            if st.button("📄 Download Cover Letter (PDF)", key="cl_pdf_btn", use_container_width=True):
                try:
                    cl_pdf = convert_html_to_pdf(cover_letter_html)
                    saved_path = save_file_to_applications(cl_pdf, cl_pdf_name, "Cover Letter PDF")
                    st.success(f"✅ Cover Letter PDF saved to: {saved_path}")
                except Exception as e:
                    st.error(f"❌ Error saving Cover Letter PDF: {str(e)}")

            if st.button("🌐 Download Cover Letter (HTML)", key="cl_html_btn", use_container_width=True):
                try:
                    saved_path = save_file_to_applications(cover_letter_html.encode('utf-8'), cl_html_name, "Cover Letter HTML")
                    st.success(f"✅ Cover Letter HTML saved to: {saved_path}")
                except Exception as e:
                    st.error(f"❌ Error saving Cover Letter HTML: {str(e)}")

        # Combined download button
        st.markdown("---")
        if st.button("📦 Download Both CV & Cover Letter (PDF)", key="both_pdf_btn", use_container_width=True):
            try:
                # Debug logging
                logger.info(f"Combined download button clicked")

                st.info("🔄 Converting CV to PDF...")
                cv_pdf = convert_html_to_pdf(cv_html)
                logger.info(f"CV PDF generated: {len(cv_pdf)} bytes")

                st.info("🔄 Converting Cover Letter to PDF...")
                cl_pdf = convert_html_to_pdf(cover_letter_html)
                logger.info(f"CL PDF generated: {len(cl_pdf)} bytes")

                st.info("🔄 Saving CV PDF...")
                cv_saved_path = save_file_to_applications(cv_pdf, cv_pdf_name, "CV PDF")
                logger.info(f"CV saved to: {cv_saved_path}")

                st.info("🔄 Saving Cover Letter PDF...")
                cl_saved_path = save_file_to_applications(cl_pdf, cl_pdf_name, "Cover Letter PDF")
                logger.info(f"CL saved to: {cl_saved_path}")

                st.success(f"✅ Both documents saved successfully!")
                st.info(f"📋 CV PDF: {cv_saved_path}")
                st.info(f"💌 Cover Letter PDF: {cl_saved_path}")
            except Exception as e:
                logger.error(f"Combined download error: {str(e)}")
                st.error(f"❌ Error saving documents: {str(e)}")
                st.exception(e)

        # Preview section
        with st.expander("👀 Preview CV"):
            st.components.v1.html(cv_html, height=600, scrolling=True)

        with st.expander("👀 Preview Cover Letter"):
            st.components.v1.html(cover_letter_html, height=600, scrolling=True)


if __name__ == "__main__":
    print("🚀 Starting AI Job Application System...")
    logger.info("Application started")
    main()