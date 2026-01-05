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
    gender = user_profile.personal_info.gender if hasattr(user_profile.personal_info, 'gender') else 'male'
    job_offer = parse_job_offer(job_offer_text, gender=gender)
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

    selected_id = st.selectbox(
        "Select an application to view details:",
        options=[app.id for app in applications],
        format_func=lambda x: next((f"{app.company} - {app.position}" for app in applications if app.id == x), "Unknown")
    )

    if selected_id:
        selected_app = next((app for app in applications if app.id == selected_id), None)
        if selected_app:
            # Use a card-like container
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])

                with col1:
                    # Header with company and position
                    st.markdown(f"### {selected_app.company}")
                    st.caption(f"{selected_app.position} • {selected_app.location}")

                    # Key metrics in a row
                    met_col1, met_col2, met_col3 = st.columns(3)
                    with met_col1:
                        st.metric("Match Rate", f"{selected_app.matching_rate:.1%}")
                    with met_col2:
                        st.metric("Cost", f"${selected_app.application_cost:.4f}")
                    with met_col3:
                        st.metric("Date", selected_app.created_at.strftime('%Y-%m-%d'))

                    # Skills section
                    if selected_app.matched_skills or selected_app.unmatched_skills:
                        st.divider()
                        if selected_app.matched_skills:
                            st.write("**Matched Skills**")
                            st.write(" ".join([f"`{skill}`" for skill in selected_app.matched_skills]))

                        if selected_app.unmatched_skills:
                            st.write("**Skills to Develop**")
                            st.write(" ".join([f"`{skill}`" for skill in selected_app.unmatched_skills]))

                with col2:
                    if st.button("Delete", type="secondary", use_container_width=True):
                        if db.delete_application(selected_id):
                            st.success("Deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete")
    else:
        st.info("Select an application to view details")


def show_template_editor_page():
    """Display the template editor page"""
    st.title("Template Editor")
    st.caption("Edit your templates directly - changes are saved to disk")

    st.info("💡 To complete your profile, edit the YAML file at: `templates/user_profile.yaml`")

    # Define template files
    templates = {
        "CV Template (HTML)": "templates/cv_template.html",
        "Cover Letter Template (HTML)": "templates/cover_letter_template.html",
    }

    # Create tabs for each template
    tabs = st.tabs(list(templates.keys()))

    for tab, (tab_name, file_path) in zip(tabs, templates.items()):
        with tab:
            # Read current file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except FileNotFoundError:
                st.error(f"File not found: {file_path}")
                continue
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
                continue

            # Display file info
            col_info1, col_info2 = st.columns([2, 1])
            with col_info1:
                st.caption(f"{file_path}")
            with col_info2:
                st.caption(f"Size: {len(original_content)} bytes")

            # For HTML templates, use side-by-side layout with preview
            if "HTML" in tab_name:
                col_edit, col_preview = st.columns([1, 1], gap="medium")

                with col_edit:
                    st.subheader("Edit")
                    st.caption("⚠️ You can edit directly the html in 'templates' directory")
                    edited_content = st.text_area(
                        f"Edit {tab_name}",
                        value=original_content,
                        height=500,
                        label_visibility="collapsed",
                        key=f"editor_{file_path}"
                    )

                with col_preview:
                    st.subheader("Live Preview (A4 Page)")
                    st.caption("⚠️ Preview is approximate - download the PDF version to see the exact match")
                    # Show live preview of HTML with A4 page dimensions (210mm x 297mm) and 1cm margins
                    try:
                        # Wrap the HTML content in A4 page container with margins matching PDF output
                        styled_html = f"""
                        <style>
                            #preview-container, #preview-container * {{
                                color: black !important;
                            }}
                            #a4-page {{
                                width: 210mm;
                                height: 297mm;
                                margin: 0 auto;
                                padding: 10mm;
                                background-color: white;
                                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                                overflow: auto;
                                font-family: Arial, sans-serif;
                                height: 500px;
                            }}
                        </style>
                        <div id="a4-page">
                            <div id="preview-container">
                                {edited_content}
                            </div>
                        </div>
                        """
                        st.html(styled_html)
                    except Exception as e:
                        st.warning(f"Preview error (syntax issue): {str(e)[:100]}")

                    # Download preview as PDF button - centered and constrained to match A4 width
                    col_spacer_l, col_btn, col_spacer_r = st.columns([0.1, 0.8, 0.1])
                    with col_btn:
                        if st.button("Download Preview (PDF)", key=f"download_preview_{file_path}", use_container_width=True, type="primary"):
                            try:
                                preview_pdf = convert_html_to_pdf(edited_content)
                                filename = f"Preview_{file_path.split('/')[-1].replace('.html', '')}.pdf"
                                saved_path = save_file_to_applications(preview_pdf, filename, "Template Preview PDF")
                                st.success(f"Saved to {saved_path}")
                            except Exception as e:
                                st.error(f"Error downloading preview: {str(e)}")

            else:
                # For YAML, just show editor
                edited_content = st.text_area(
                    f"Edit {tab_name}",
                    value=original_content,
                    height=500,
                    label_visibility="collapsed",
                    key=f"editor_{file_path}"
                )

            # Only show save section if content has changed
            if edited_content != original_content:
                st.info("Changes detected")

                col_save1, col_save2 = st.columns(2)

                with col_save1:
                    if st.button("💾 Save Changes", key=f"save_{file_path}", use_container_width=True, type="primary"):
                        # Validate content based on file type
                        is_valid = True
                        error_msg = ""

                        if "YAML" in tab_name:
                            try:
                                yaml.safe_load(edited_content)
                            except yaml.YAMLError as e:
                                is_valid = False
                                error_msg = f"YAML Syntax Error: {str(e)}"
                        elif "HTML" in tab_name:
                            # Basic HTML validation - check for matching tags
                            if edited_content.count('<') != edited_content.count('>'):
                                is_valid = False
                                error_msg = "HTML Syntax Error: Mismatched angle brackets"

                        if is_valid:
                            try:
                                # Save the file
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(edited_content)
                                st.success(f"✅ {tab_name} saved successfully!")
                                st.balloons()
                                logger.info(f"Template saved: {file_path}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving file: {str(e)}")
                                logger.error(f"Error saving template {file_path}: {str(e)}")
                        else:
                            st.error(f"❌ Cannot save - {error_msg}")

                with col_save2:
                    if st.button("⚠️ Discard Changes", key=f"discard_{file_path}", use_container_width=True):
                        st.rerun()
            else:
                st.caption("No changes made")


def show_follow_up_page():
    """Display the application follow-up page"""
    st.title("Data Visualization")
    st.subheader("Total Metrics")

    db = ApplicationDatabase()
    applications = db.get_all_applications()

    if not applications:
        st.info("No applications found. Generate your first application on the main page!")
        return

    # Summary metrics
    total_cost = db.get_total_cost()
    avg_match_rate = sum(app.matching_rate for app in applications) / len(applications)
    avg_cost = total_cost / len(applications) if len(applications) > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Applications", len(applications))
    with col2:
        st.metric("Average Match", f"{avg_match_rate:.1%}")
    with col3:
        st.metric("Total Cost", f"${total_cost:.4f}")
    with col4:
        st.metric("Average Cost", f"${avg_cost:.4f}")

    # Today's metrics
    st.divider()
    st.subheader("Today's Metrics")

    today = datetime.now().date()
    today_applications = [app for app in applications if app.created_at.date() == today]

    if today_applications:
        today_total_cost = sum(app.application_cost for app in today_applications)
        today_avg_match_rate = sum(app.matching_rate for app in today_applications) / len(today_applications)
        today_avg_cost = today_total_cost / len(today_applications) if len(today_applications) > 0 else 0

        col_today1, col_today2, col_today3, col_today4 = st.columns(4)
        with col_today1:
            st.metric("Total Applications", len(today_applications))
        with col_today2:
            st.metric("Average Match", f"{today_avg_match_rate:.1%}")
        with col_today3:
            st.metric("Total Cost", f"${today_total_cost:.4f}")
        with col_today4:
            st.metric("Average Cost", f"${today_avg_cost:.4f}")
    else:
        st.info("No applications generated today")

    # Analytics section
    if len(applications) >= 3:  # Only show analytics if we have enough data
        st.subheader("Analytics")

        try:
            import plotly.express as px
            import pandas as pd
        except ImportError:
            st.error("Plotly and pandas are required for analytics. Install with: pip install plotly pandas")
            return

        # Applications generated per day (past 10 days)
        # Generate all dates for the past 10 days
        from datetime import timedelta
        today = datetime.now().date()
        date_range = [today - timedelta(days=i) for i in range(10, -1, -1)]

        apps_by_date_gen = sorted(applications, key=lambda x: x.created_at)
        daily_counts = pd.DataFrame({
            'Date': [app.created_at.date() for app in apps_by_date_gen]
        }).groupby('Date').size().reset_index(name='Count')

        # Create a complete date range DataFrame and merge with actual counts
        date_range_df = pd.DataFrame({'Date': date_range})
        daily_counts_complete = date_range_df.merge(daily_counts, on='Date', how='left').fillna(0)
        daily_counts_complete['Count'] = daily_counts_complete['Count'].astype(int)

        fig_daily = px.line(daily_counts_complete, x='Date', y='Count',
                           title='Applications Generated Per Day (Past 10 Days)',
                           labels={'Count': 'Number of Applications'},
                           markers=True)
        fig_daily.update_layout(showlegend=False)
        fig_daily.update_xaxes(tickformat='%b %d')
        st.plotly_chart(fig_daily, use_container_width=True)

        # Match rate trend - calculate daily average
        apps_by_date = sorted(applications, key=lambda x: x.created_at)

        # Group applications by date and calculate average match rate
        daily_match_rates = pd.DataFrame({
            'Date': [app.created_at.date() for app in apps_by_date],
            'Match Rate': [app.matching_rate * 100 for app in apps_by_date]
        }).groupby('Date')['Match Rate'].mean().reset_index()

        # Create a complete date range DataFrame and merge with actual match rates
        date_range_df = pd.DataFrame({'Date': date_range})
        daily_match_rates_complete = date_range_df.merge(daily_match_rates, on='Date', how='left').fillna(0)

        fig = px.line(daily_match_rates_complete, x='Date', y='Match Rate',
                     title='Daily Average Match Rate (Past 10 Days)',
                     labels={'Match Rate': 'Match Rate (%)'})
        fig.update_layout(showlegend=False)
        fig.update_xaxes(tickformat='%b %d')
        st.plotly_chart(fig, use_container_width=True)

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
        page_icon="🫰🏿",
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

        p, span, div, label {
            color: #F0F4EF !important;
        }

        /* Force white text in main content area */
        .main p, .main span, .main label, .main caption {
            color: #F0F4EF !important;
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
    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)

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
            "Data Visualization",
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

    with nav_col4:
        if st.button(
            "Template Editor",
            use_container_width=True,
            type="primary" if st.session_state.current_page == "⚙️ Template Editor" else "secondary"
        ):
            st.session_state.current_page = "⚙️ Template Editor"
            st.rerun()

    st.divider()

    if st.session_state.current_page == "📊 Follow-Up Dashboard":
        show_follow_up_page()
        return

    if st.session_state.current_page == "📋 Historics":
        show_historics_page()
        return

    if st.session_state.current_page == "⚙️ Template Editor":
        show_template_editor_page()
        return

    st.title("Job Application Generator")
    st.caption("Generate tailored CVs and cover letters by analyzing job offers")

    # Sidebar for user profile
    st.sidebar.header("User Profile")

    # Load user profile
    default_profile_path = "templates/user_profile.yaml"

    if os.path.exists(default_profile_path):
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

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Job Offer")
        with st.container(border=True):
            job_offer_text = st.text_area(
               "" ,
                height=400,
                placeholder="Paste the complete job offer description, requirements, and any other relevant information..."
            )

    with col2:
        st.subheader("Profile Summary")
        if 'user_profile' in locals():
            with st.container(border=True):
                st.write(f"## 👤 {user_profile.personal_info.name}")
                st.divider()

                # Skills
                with st.expander(f"Skills ({len(user_profile.skills)})"):
                    if user_profile.skills:
                        cols = st.columns(2)
                        for idx, skill in enumerate(user_profile.skills):
                            with cols[idx % 2]:
                                st.text(f"• {skill}")
                    else:
                        st.caption("No skills added yet")
                

                # Projects
                with st.expander(f"Projects ({len(user_profile.projects)})"):
                    if user_profile.projects:
                        for project in user_profile.projects[:30]:
                            st.text(f"• {project.title}")
                    else:
                        st.caption("No projects added yet")

                # Experiences
                with st.expander(f"Experiences ({len(user_profile.experiences)})"):
                    if user_profile.experiences:
                        for exp in user_profile.experiences[:10]:
                            st.text(f"• {exp.role} @ {exp.company}")
                        if len(user_profile.experiences) > 2:
                            st.caption(f"... and {len(user_profile.experiences) - 2} more")
                    else:
                        st.caption("No experiences added yet")
                st.caption("⚠️ You can edit those information in the file located at templates/user_profile.yaml")

    # Sidebar session info
    st.sidebar.divider()
    st.sidebar.subheader("Session Info")

    cost_tracker = get_cost_tracker()
    db = ApplicationDatabase()
    applications = db.get_all_applications()

    if cost_tracker.total_calls > 0:
        st.sidebar.metric("Session Cost", f"${cost_tracker.total_cost:.4f}")

    if applications:

        # Today's metrics
        today = datetime.now().date()
        today_applications = [app for app in applications if app.created_at.date() == today]

        if today_applications:
            today_total_cost = sum(app.application_cost for app in today_applications)
            today_avg_cost = today_total_cost / len(today_applications) if len(today_applications) > 0 else 0

            st.sidebar.metric("Today's Applications", len(today_applications))
            st.sidebar.metric("Today's Avg Cost", f"${today_avg_cost:.4f}")
        else:
            st.sidebar.caption("No applications today")

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