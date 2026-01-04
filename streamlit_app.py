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


def show_historics_page():
    """Display the historics page with table format view of applications"""
    st.title("Historics")
    st.caption("View all applications in table format")

    db = ApplicationDatabase()
    applications = db.get_all_applications()

    if not applications:
        st.info("No applications found. Generate your first application on the main page!")
        return

    try:
        import pandas as pd
    except ImportError:
        st.error("Pandas is required for table view. Install with: pip install pandas")
        return

    # Create DataFrame from applications
    data = []
    for app in applications:
        data.append({
            'Date': app.created_at.strftime('%Y-%m-%d'),
            'Company': app.company,
            'Position': app.position,
            'Location': app.location,
            'Match Rate': f"{app.matching_rate:.1%}",
            'Matched Skills': len(app.matched_skills),
            'Unmatched Skills': len(app.unmatched_skills),
            'Cost': f"${app.application_cost:.4f}",
            'ID': app.id
        })

    df = pd.DataFrame(data)

    # Display table
    st.subheader(f"All Applications ({len(df)})")
    st.dataframe(
        df.drop('ID', axis=1),
        use_container_width=True,
        hide_index=True,
        height=600
    )

    # Action buttons section
    st.subheader("Actions")
    col_actions1, col_actions2 = st.columns(2)

    with col_actions1:
        selected_id = st.selectbox(
            "Select an application to view details:",
            options=[app.id for app in applications],
            format_func=lambda x: next((f"{app.company} - {app.position}" for app in applications if app.id == x), "Unknown")
        )

        if selected_id:
            selected_app = next((app for app in applications if app.id == selected_id), None)
            if selected_app:
                st.write(f"**Position:** {selected_app.position}")
                st.write(f"**Company:** {selected_app.company}")
                st.write(f"**Location:** {selected_app.location}")
                st.write(f"**Date:** {selected_app.created_at.strftime('%Y-%m-%d')}")
                st.write(f"**Match Rate:** {selected_app.matching_rate:.1%}")
                st.write(f"**Cost:** ${selected_app.application_cost:.4f}")

                if selected_app.matched_skills:
                    st.write("**Matched Skills:**")
                    for skill in selected_app.matched_skills:
                        st.text(f"• {skill}")

                if selected_app.unmatched_skills:
                    st.write("**Skills to Develop:**")
                    for skill in selected_app.unmatched_skills:
                        st.text(f"• {skill}")

    with col_actions2:
        if selected_id and st.button("Delete Selected Application", type="secondary", use_container_width=True):
            if db.delete_application(selected_id):
                st.success("Application deleted successfully!")
                st.rerun()
            else:
                st.error("Failed to delete application")


def show_follow_up_page():
    """Display the application follow-up page"""
    st.title("Data Visualizationtory")
    st.caption("Track and manage your job applications")

    db = ApplicationDatabase()
    applications = db.get_all_applications()

    if not applications:
        st.info("No applications found. Generate your first application on the main page!")
        return

    # Summary metrics
    total_cost = db.get_total_cost()
    avg_match_rate = sum(app.matching_rate for app in applications) / len(applications)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Applications", len(applications))
    with col2:
        st.metric("Average Match", f"{avg_match_rate:.1%}")
    with col3:
        st.metric("Total Cost", f"${total_cost:.4f}")

    # Filters
    st.subheader("Filter Applications")
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

    # Analytics section
    if len(applications) >= 3:  # Only show analytics if we have enough data
        st.subheader("Analytics")

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
        st.subheader("Skills Gap Analysis")

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
            st.subheader("Development Insights")
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

    # Custom color theme
    st.markdown("""
    <style>
        :root {
            --primary-dark: #0D1821;
            --accent-teal: #0F7173;
            --background-light: #F0F4EF;
        }

        /* Main background */
        .main {
            background-color: #0D1821;
            color: #F0F4EF;
        }

        /* Sidebar */
        [data-testid="sidebar"] {
            background-color: #0D1821;
        }

        /* Text elements */
        h1, h2, h3, h4, h5, h6 {
            color: #F0F4EF;
        }

        p, span, div {
            color: #F0F4EF;
        }

        /* Primary buttons (active tab) */
        .stButton > button[kind="primary"] {
            background-color: #0F7173;
            color: #F0F4EF;
            font-weight: 700;
            transition: background-color 0.2s ease;
            text-decoration: none;
            border: none;
        }

        .stButton > button[kind="primary"]:hover {
            background-color: rgba(15, 113, 115, 0.8);
            color: #F0F4EF;
        }

        /* Secondary buttons (inactive tab) */
        .stButton > button[kind="secondary"] {
            background-color: transparent;
            color: #F0F4EF;
            font-weight: normal;
            transition: all 0.2s ease;
            border: 1px solid #0F7173;
        }

        .stButton > button[kind="secondary"]:hover {
            background-color: rgba(15, 113, 115, 0.2);
            color: #F0F4EF;
            border-color: #0F7173;
        }

        /* Input fields - general default */
        input,
        textarea,
        select {
            border-color: #0F7173 !important;
            background-color: #0D1821 !important;
            color: #F0F4EF !important;
        }

        /* Input fields */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > select,
        .stMultiSelect > div > div > select {
            border: 2px solid #0F7173 !important;
            background-color: #0D1821 !important;
            color: #F0F4EF !important;
        }

        /* General input focus state */
        input:focus,
        textarea:focus,
        select:focus {
            border-top-color: #0F7173 !important;
            border-right-color: #0F7173 !important;
            border-bottom-color: #0F7173 !important;
            border-left-color: #0F7173 !important;
            outline: none !important;
            background-color: #0D1821 !important;
        }

        /* Input fields focus state */
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stSelectbox > div > div > select:focus,
        .stMultiSelect > div > div > select:focus {
            border-top-color: #0F7173 !important;
            border-right-color: #0F7173 !important;
            border-bottom-color: #0F7173 !important;
            border-left-color: #0F7173 !important;
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(15, 113, 115, 0.2) !important;
            background-color: #0D1821 !important;
        }

        /* Streamlit textarea focus state */
        .stTextAreaRootElement:focus,
        .st-b5:focus,
        .st-b3:focus,
        .st-b4:focus,
        .st-b6:focus {
            border-top-color: #0F7173 !important;
            border-right-color: #0F7173 !important;
            border-bottom-color: #0F7173 !important;
            border-left-color: #0F7173 !important;
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(15, 113, 115, 0.2) !important;
        }

        /* Streamlit wrapper classes focus state */
        .st-b3:focus,
        .st-b4:focus,
        .st-b5:focus,
        .st-b6:focus {
            border-top-color: #0F7173 !important;
            border-right-color: #0F7173 !important;
            border-bottom-color: #0F7173 !important;
            border-left-color: #0F7173 !important;
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(15, 113, 115, 0.2) !important;
        }

        /* Info/success/warning/error messages */
        .stAlert {
            background-color: rgba(15, 113, 115, 0.15);
            color: #F0F4EF;
            border: 2px solid #0F7173;
        }

        /* Override default Streamlit error styling (red) with teal */
        [data-testid="stAlert"] {
            background-color: rgba(15, 113, 115, 0.15) !important;
            border-color: #0F7173 !important;
            color: #F0F4EF !important;
        }

        /* Override error icon and text colors */
        [data-testid="stAlert"] svg {
            color: #0F7173 !important;
            fill: #0F7173 !important;
        }

        [data-testid="stAlert"] > * {
            color: #F0F4EF !important;
        }

        /* Streamlit error container */
        .st-emotion-cache-1v0mbdj {
            background-color: rgba(15, 113, 115, 0.15) !important;
            border: 2px solid #0F7173 !important;
            color: #F0F4EF !important;
        }

        /* Danger/error state override */
        [role="alert"] {
            background-color: rgba(15, 113, 115, 0.15) !important;
            border-color: #0F7173 !important;
            color: #F0F4EF !important;
        }

        [role="alert"] svg {
            color: #0F7173 !important;
            fill: #0F7173 !important;
        }

        /* Metric containers */
        .stMetric {
            background-color: rgba(15, 113, 115, 0.15);
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #0F7173;
        }

        /* Dividers */
        .stHorizontalBlock {
            border-color: #0F7173;
        }

        hr {
            border-color: #0F7173 !important;
        }

        /* Tabs */
        .stTabs [role="tablist"] {
            border-color: #0F7173;
        }

        .stTabs [role="tab"] {
            color: #F0F4EF;
            border-bottom-color: transparent;
        }

        .stTabs [role="tab"][aria-selected="true"] {
            color: #F0F4EF;
            border-bottom-color: #0F7173;
            font-weight: 600;
        }

        /* Expander */
        .streamlit-expanderHeader {
            background-color: rgba(15, 113, 115, 0.15);
            color: #F0F4EF;
        }

        /* Code blocks */
        .stCodeBlock {
            background-color: #0D1821;
            color: #F0F4EF;
            border: 1px solid #0F7173;
        }

        /* Caption and help text */
        .stCaption, .stHelp {
            color: #F0F4EF;
        }

        /* DataFrames */
        .streamlit-dataframe {
            background-color: #0D1821;
            color: #F0F4EF;
        }

        /* Plotly charts background */
        .plotly-graph-div {
            background-color: transparent;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: #0D1821;
        }

        ::-webkit-scrollbar-thumb {
            background: #0F7173;
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: rgba(15, 113, 115, 0.8);
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state for page tracking
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🚀 Generate Application"

    # Top navigation bar
    nav_col1, nav_col2, nav_col3 = st.columns(3)

    with nav_col1:
        if st.button(
            "Generate Application",
            use_container_width=True,
            type="primary" if st.session_state.current_page == "🚀 Generate Application" else "secondary"
        ):
            st.session_state.current_page = "🚀 Generate Application"
            st.rerun()

    with nav_col2:
        if st.button(
            "Data Visualizationtory",
            use_container_width=True,
            type="primary" if st.session_state.current_page == "📊 Follow-Up Dashboard" else "secondary"
        ):
            st.session_state.current_page = "📊 Follow-Up Dashboard"
            st.rerun()

    with nav_col3:
        if st.button(
            "Historics",
            use_container_width=True,
            type="primary" if st.session_state.current_page == "📋 Historics" else "secondary"
        ):
            st.session_state.current_page = "📋 Historics"
            st.rerun()

    st.divider()

    if st.session_state.current_page == "📊 Follow-Up Dashboard":
        show_follow_up_page()
        return

    if st.session_state.current_page == "📋 Historics":
        show_historics_page()
        return

    st.title("Job Application Generator")
    st.caption("Generate tailored CVs and cover letters by analyzing job offers")

    # Sidebar for user profile
    st.sidebar.header("User Profile")

    # Check if default profile exists
    default_profile_path = "templates/user_profile.yaml"

    if os.path.exists(default_profile_path):
        use_default = st.sidebar.checkbox("Use default profile", value=True)
        if use_default:
            with open(default_profile_path, 'r', encoding='utf-8') as f:
                profile_data = yaml.safe_load(f)
            user_profile = UserProfile(**profile_data)
            st.sidebar.caption(f"Profile: {user_profile.personal_info.name}")
        else:
            uploaded_profile = st.sidebar.file_uploader(
                "Upload your profile (YAML)",
                type=['yaml', 'yml'],
                help="Upload a YAML file with your profile information"
            )
            if uploaded_profile:
                profile_data = yaml.safe_load(uploaded_profile)
                user_profile = UserProfile(**profile_data)
                st.sidebar.caption(f"Profile: {user_profile.personal_info.name}")
            else:
                st.sidebar.info("Please upload a profile file")
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
            st.sidebar.caption(f"Profile: {user_profile.personal_info.name}")
        else:
            st.sidebar.info("Please upload a profile file")
            st.stop()

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Job Offer")
        job_offer_text = st.text_area(
            "Paste the job offer text here:",
            height=400,
            placeholder="Paste the complete job offer description, requirements, and any other relevant information..."
        )

    with col2:
        st.subheader("Profile Summary")
        if 'user_profile' in locals():
            st.write(f"**Name:** {user_profile.personal_info.name}")
            st.write(f"**Email:** {user_profile.personal_info.email}")
            st.write(f"**Skills:** {len(user_profile.skills)} total")
            st.write(f"**Projects:** {len(user_profile.projects)} available")
            st.write(f"**Experiences:** {len(user_profile.experiences)} entries")
            st.write(f"**Languages:** {', '.join(user_profile.languages)}")

    # Sidebar session info
    st.sidebar.divider()
    st.sidebar.subheader("Session Info")

    cost_tracker = get_cost_tracker()
    db = ApplicationDatabase()
    applications = db.get_all_applications()

    if cost_tracker.total_calls > 0:
        st.sidebar.metric("Session Cost", f"${cost_tracker.total_cost:.4f}")

    if applications:
        st.sidebar.metric("Total Applications", len(applications))
        total_cost = db.get_total_cost()
        st.sidebar.metric("All-Time Cost", f"${total_cost:.4f}")

    # Generate button
    if st.button("Generate CV & Cover Letter", type="primary", use_container_width=True):
        if not job_offer_text.strip():
            st.error("Please enter a job offer description")
            st.stop()

        try:
            with st.spinner("Analyzing job offer and generating documents..."):
                cv_html, cover_letter_html, job_offer, matched_skills, application_id = process_job_application(job_offer_text, user_profile)

            # Store in session state for persistence across reruns
            st.session_state.cv_html = cv_html
            st.session_state.cover_letter_html = cover_letter_html
            st.session_state.job_offer = job_offer
            st.session_state.matched_skills = matched_skills
            st.session_state.application_id = application_id

            st.success(f"Documents generated successfully (ID: {application_id})")

            # Display cost information
            cost_tracker = get_cost_tracker()
            if cost_tracker.total_calls > 0:
                with st.expander("Cost Details"):
                    col_cost1, col_cost2, col_cost3 = st.columns(3)
                    with col_cost1:
                        st.metric("Total Cost", f"${cost_tracker.total_cost:.4f}")
                    with col_cost2:
                        st.metric("API Calls", cost_tracker.total_calls)
                    with col_cost3:
                        st.metric("Tokens", f"{cost_tracker.total_tokens:,}")

            # Display job analysis results
            st.subheader("Job Analysis")

            col_job, col_skills = st.columns(2)

            with col_job:
                st.write(f"**Position:** {job_offer.job_title}")
                st.write(f"**Company:** {job_offer.company_name}")
                st.write(f"**Location:** {job_offer.location}")
                st.caption("Required Skills")
                for skill in job_offer.skills_required:
                    st.text(f"• {skill}")

            with col_skills:
                total_required = len(job_offer.skills_required)
                matched_count = len(matched_skills.matched_skills)
                match_percentage = (matched_count / total_required * 100) if total_required > 0 else 0.0
                st.metric("Match Rate", f"{matched_count}/{total_required}")
                st.metric("Coverage", f"{match_percentage:.0f}%")

                if matched_skills.matched_skills:
                    st.caption("Matched Skills")
                    for skill in matched_skills.matched_skills:
                        st.text(f"• {skill}")

                if len(matched_skills.matched_skills) < len(job_offer.skills_required):
                    missing_skills = set(job_offer.skills_required) - set(matched_skills.matched_skills)
                    st.caption("Not Matched")
                    for skill in missing_skills:
                        st.text(f"• {skill}")

        except Exception as e:
            st.error(f"Error generating documents: {str(e)}")
            st.exception(e)

    # Download section - available if documents exist in session state
    if hasattr(st.session_state, 'cv_html') and hasattr(st.session_state, 'cover_letter_html'):
        st.subheader("Download Documents")

        # Get data from session state
        cv_html = st.session_state.cv_html
        cover_letter_html = st.session_state.cover_letter_html
        job_offer = st.session_state.job_offer

        # Generate clean filenames
        company_clean = "".join(c for c in job_offer.company_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        position_clean = "".join(c for c in job_offer.job_title if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')

        cv_pdf_name = f"CV_{company_clean}_{position_clean}.pdf"
        cv_html_name = f"CV_{company_clean}_{position_clean}.html"
        cl_pdf_name = f"Cover_Letter_{company_clean}_{position_clean}.pdf"
        cl_html_name = f"Cover_Letter_{company_clean}_{position_clean}.html"

        col_cv, col_cl = st.columns(2)

        with col_cv:
            st.write("**CV**")
            if st.button("Download PDF", key="cv_pdf_btn", use_container_width=True):
                try:
                    cv_pdf = convert_html_to_pdf(cv_html)
                    saved_path = save_file_to_applications(cv_pdf, cv_pdf_name, "CV PDF")
                    logger.info(f"CV PDF saved to: {saved_path}")
                    st.success(f"Saved to {saved_path}")
                except Exception as e:
                    logger.error(f"Error saving CV PDF: {str(e)}")
                    st.error(f"Error: {str(e)}")

            if st.button("Download HTML", key="cv_html_btn", use_container_width=True):
                try:
                    saved_path = save_file_to_applications(cv_html.encode('utf-8'), cv_html_name, "CV HTML")
                    logger.info(f"CV HTML saved to: {saved_path}")
                    st.success(f"Saved to {saved_path}")
                except Exception as e:
                    logger.error(f"Error saving CV HTML: {str(e)}")
                    st.error(f"Error: {str(e)}")

        with col_cl:
            st.write("**Cover Letter**")
            if st.button("Download PDF", key="cl_pdf_btn", use_container_width=True):
                try:
                    cl_pdf = convert_html_to_pdf(cover_letter_html)
                    saved_path = save_file_to_applications(cl_pdf, cl_pdf_name, "Cover Letter PDF")
                    st.success(f"Saved to {saved_path}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

            if st.button("Download HTML", key="cl_html_btn", use_container_width=True):
                try:
                    saved_path = save_file_to_applications(cover_letter_html.encode('utf-8'), cl_html_name, "Cover Letter HTML")
                    st.success(f"Saved to {saved_path}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

        # Combined download button
        st.divider()
        if st.button("Download Both (PDF)", key="both_pdf_btn", use_container_width=True):
            try:
                logger.info("Combined download button clicked")
                cv_pdf = convert_html_to_pdf(cv_html)
                cl_pdf = convert_html_to_pdf(cover_letter_html)
                save_file_to_applications(cv_pdf, cv_pdf_name, "CV PDF")
                save_file_to_applications(cl_pdf, cl_pdf_name, "Cover Letter PDF")
                st.success("Documents saved successfully!")
            except Exception as e:
                logger.error(f"Combined download error: {str(e)}")
                st.error(f"Error: {str(e)}")

        # Preview section
        with st.expander("Preview CV"):
            cv_wrapped = f'<div style="background-color: white; padding: 20px; border-radius: 8px;">{cv_html}</div>'
            st.components.v1.html(cv_wrapped, height=600, scrolling=True)

        with st.expander("Preview Cover Letter"):
            cl_wrapped = f'<div style="background-color: white; padding: 20px; border-radius: 8px;">{cover_letter_html}</div>'
            st.components.v1.html(cl_wrapped, height=600, scrolling=True)


if __name__ == "__main__":
    print("🚀 Starting AI Job Application System...")
    logger.info("Application started")
    main()