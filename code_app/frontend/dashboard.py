from nicegui import ui
import pandas as pd
import plotly.graph_objects as go
import asyncio
import json
import logging
import numpy as np
import os
import sys
import aiohttp

# Get project root directory dynamically and add to path for absolute imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API configuration - use environment variable for production
API_BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:8001')

# Global references for shared UI containers and elements
report_container_ref = None
status_container_ref = None
suggestions_area_ref = None
mobile_nav_ref = None
agent_data_preview_ref = None

TABLE_STYLES = '''
.spectral-table-html table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9em;
}
.spectral-table-html thead th {
    position: sticky !important;
    top: 0 !important;
    background: #f8fafc !important; /* Lighter header */
    z-index: 1001 !important;
    border-bottom: 2px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    padding: 12px 8px; /* Increased padding */
    font-weight: bold;
    color: #334155;
}
.spectral-table-html thead th:hover {
    z-index: 1012 !important; /* Bring hovered header above its siblings */
}
.spectral-table-html thead th:last-child {
    border-right: none;
}
/* Visual highlighting for core columns */
.spectral-table-html thead th.core-column {
    background: #f1f5f9 !important;
}
.spectral-table-html tbody tr:nth-child(even) {
    background-color: #f8fafc; /* Zebra-striping */
}
.spectral-table-html tbody tr:hover {
    background-color: #f1f5f9; /* Softer hover */
}
.spectral-table-html tbody td {
    padding: 10px 24px 10px 8px; /* Increased right padding for medal icons */
    border-bottom: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    color: #475569;
    font-weight: bold;
    position: relative;
}
.spectral-table-html tbody td:last-child {
    border-right: none;
}
.spectral-table-html .model-cell {
    font-weight: bold;
    color: #1e293b;
}
.spectral-table-html .rank-cell {
    font-weight: 600;
    color: #0284c7;
}
/* Top 3 ranking styles for cells - Clean and modern design */
.spectral-table-html .first-place-cell {
    background-color: #fef3c7 !important;
    color: #92400e !important;
    font-weight: 600 !important;
    position: relative !important;
}
.spectral-table-html .first-place-cell::after {
    content: "🥇";
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.8em;
    opacity: 0.7;
}
.spectral-table-html .second-place-cell {
    background-color: #f1f5f9 !important;
    color: #334155 !important;
    font-weight: 600 !important;
    position: relative !important;
}
.spectral-table-html .second-place-cell::after {
    content: "🥈";
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.8em;
    opacity: 0.7;
}
.spectral-table-html .third-place-cell {
    background-color: #fef2f2 !important;
    color: #7f1d1d !important;
    font-weight: 600 !important;
    position: relative !important;
}
.spectral-table-html .third-place-cell::after {
    content: "🥉";
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.8em;
    opacity: 0.7;
}
.top-3-legend {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: #f8fafc;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
}
.legend-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
}
.legend-color {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 2px solid rgba(0,0,0,0.1);
}
.legend-color.first {
    background-color: #fef3c7;
    border-color: #f59e0b;
}
.legend-color.second {
    background-color: #f1f5f9;
    border-color: #64748b;
}
.legend-color.third {
    background-color: #fef2f2;
    border-color: #dc2626;
}
.spectral-table-html {
    position: relative;
}
.spectral-table-html table .toggleable-col {
    display: none;
}
.spectral-table-html table.show-details .toggleable-col {
    display: table-cell;
}
.sortable-header {
    cursor: pointer;
    position: relative;
    white-space: nowrap;
}
.sort-icons {
    display: inline-flex;
    flex-direction: column;
    margin-left: 6px;
    position: relative;
    top: 2px;
}
.sort-icons .material-symbols-outlined {
    font-size: 1.2rem;
    line-height: 0.6;
    color: #cbd5e1; /* Inactive color */
}
.sortable-header:hover .sort-icons .material-symbols-outlined {
    color: #94a3b8; /* Hover color */
}
.sortable-header.sorted-asc .sort-icon-up,
.sortable-header.sorted-desc .sort-icon-down {
    color: #334155; /* Active sort color */
}
.tooltip-container {
    position: relative;
    display: inline-flex;
    align-items: center;
}
.tooltip-container .tooltip-text {
    white-space: normal; /* Allow tooltip text to wrap */
    visibility: hidden;
    width: 260px;
    background-color: #1f2937;
    color: #fff;
    text-align: left;
    border-radius: 6px;
    padding: 10px 12px;
    position: absolute;
    z-index: 1010;
    top: 140%; /* Changed from bottom to top */
    left: 50%;
    margin-left: -130px;
    opacity: 0;
    transition: opacity 0.3s;
    font-size: 0.875rem;
    font-weight: 400;
    line-height: 1.6;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.tooltip-container:hover .tooltip-text {
    visibility: visible;
    opacity: 1;
}
.tooltip-container .tooltip-text::after {
    content: "";
    position: absolute;
    bottom: 100%; /* Changed from top to bottom */
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: transparent transparent #1f2937 transparent; /* Arrow points up */
}
/* Flexbox for even column distribution in Arena table */
.arena-table-layout th,
.arena-table-layout td {
    word-wrap: break-word;
}
.arena-table-layout th:not(:first-child),
.arena-table-layout td:not(:first-child) {
    flex: 1;
}
.arena-table-layout th:first-child,
.arena-table-layout td:first-child {
    justify-content: flex-start; /* Keep model name left-aligned */
}
/* New styles for the step-by-step cards */
.grid-container {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 2rem;
    margin-top: 1.5rem;
}
.step-card {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05), 0 10px 20px rgba(0,0,0,0.05);
    border: 1px solid #e2e8f0;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    display: flex;
    flex-direction: column;
    height: 100%; /* Ensure cards in the same row have the same height */
}
.step-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 15px rgba(0,0,0,0.07), 0 15px 30px rgba(0,0,0,0.07);
}
.card-header {
    display: flex;
    align-items: center;
    margin-bottom: 1.5rem;
}
.card-icon-container {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 60px; /* Slightly smaller icon container */
    height: 60px;
    background-color: #eef2ff; /* Light blue background */
    border-radius: 50%;
    margin-right: 1rem; /* Space between icon and title */
    flex-shrink: 0;
}
.card-icon {
    font-size: 2.25rem; /* Slightly smaller icon */
    color: #011f5b;
}
.card-title {
    font-size: 1.25rem;
    font-weight: 800;
    color: #1e293b;
}
.card-description {
    font-size: 0.95rem;
    color: #475569;
    line-height: 1.6;
    flex-grow: 1; /* Allow description to fill space */
}
.card-description strong {
    color: #011f5b;
    font-weight: 600;
}
.card-description ul {
    margin-top: 1rem;
    padding-left: 0; /* Remove default padding */
    list-style: none; /* Remove default bullets */
}
.card-description li {
    display: flex;
    align-items: flex-start;
    margin-bottom: 0.75rem;
}
.card-description li .material-symbols-outlined {
    font-size: 1.25rem;
    color: #011f5b;
    margin-right: 0.75rem;
    flex-shrink: 0;
    margin-top: 2px;
}
.card-description .benchmark-item {
    margin-bottom: 1rem;
}
.card-description .benchmark-item strong {
    display: inline;
    margin-bottom: 0;
}
.advantage-list {
    margin-top: 0.75rem;
    padding-left: 0.5rem;
}
.advantage-item {
    display: flex;
    align-items: flex-start;
    margin-bottom: 0.75rem;
}
.advantage-item .material-symbols-outlined {
    font-size: 1.1rem;
    color: #3b82f6; /* A slightly lighter blue */
    margin-right: 0.5rem;
    margin-top: 3px;
    flex-shrink: 0;
}
.advantage-item strong {
    font-weight: 600;
    color: #1e293b;
}
.advantage-item p {
    font-size: 0.9rem;
    color: #64748b;
    margin: 0;
    padding: 0;
}
.card-footer {
    margin-top: 1.5rem;
    font-size: 0.875rem;
    color: #64748b;
}
/* Spectral Ranking Detail button styling */
.spectral-detail-button {
    color: white !important;
}
/* Responsive layout for smaller screens */
@media (max-width: 992px) {
    .grid-container {
        grid-template-columns: 1fr;
    }
}
/* Adjust tooltip position for the last two columns to prevent overflow */
.spectral-table-html thead th:nth-last-child(1) .tooltip-container .tooltip-text,
.spectral-table-html thead th:nth-last-child(2) .tooltip-container .tooltip-text {
    left: auto;
    right: 0;
    margin-left: 0;
}
.spectral-table-html thead th:nth-last-child(1) .tooltip-container .tooltip-text::after,
.spectral-table-html thead th:nth-last-child(2) .tooltip-container .tooltip-text::after {
    left: auto;
    right: 20px;
}
/* Mode Selection Cards */
.mode-card {
    flex: 1;
    max-width: 684px;
    padding: 2.5rem;
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
    display: flex;
    flex-direction: column;
    text-align: left;
    border: 2px solid transparent;
}
.mode-card.active {
    border-color: #011f5b;
    background-color: #ffffff;
    box-shadow: 0 10px 20px rgba(0,0,0,0.08), 0 6px 6px rgba(0,0,0,0.1);
    transform: translateY(-5px);
}
.mode-card.inactive {
    background-color: #f1f5f9;
    border-color: #e2e8f0;
    opacity: 0.8;
}
.mode-card.inactive:hover {
    opacity: 1;
    transform: translateY(-2px);
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}
.mode-card .card-icon-wrapper {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    background-color: #eef2ff;
    width: 64px;
    height: 64px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}
.mode-card .card-title {
    font-size: 1.5rem;
    font-weight: 800;
    margin-bottom: 0.75rem;
    color: #011f5b;
}
.mode-card .card-description {
    font-size: 0.95rem;
    line-height: 1.6;
    color: #475569;
    margin-bottom: 1.5rem;
    flex-grow: 1;
}
.mode-card .card-features {
    list-style: none;
    padding: 0;
    margin: 0;
}
.mode-card .card-features li {
    display: flex;
    align-items: center;
    font-size: 0.9rem;
    color: #1e293b;
    margin-bottom: 0.5rem;
    font-weight: 500;
}
.mode-card .card-features li .material-symbols-outlined {
    font-size: 1.25rem;
    margin-right: 0.75rem;
    color: #011f5b;
}
.mode-card.inactive .card-title,
.mode-card.inactive .card-features li .material-symbols-outlined {
    color: #475569;
}
/* Compare card styles */
.compare-card {
    border-radius: 12px;
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    transition: all 0.3s ease;
}
.compare-card:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.compare-card .compare-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
}
.compare-card .compare-icon {
    display: inline-flex;
    width: 40px;
    height: 40px;
    border-radius: 9999px;
    background: #eef2ff;
    align-items: center;
    justify-content: center;
    color: #011f5b;
    font-size: 1.25rem;
}
.compare-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    align-items: start;
}
@media (min-width: 640px) {
    .compare-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (min-width: 768px) {
    .compare-grid { grid-template-columns: repeat(2, 1fr); }
}
.helper-text {
    font-size: 0.85rem;
    color: #64748b;
}
.primary-btn {
    background-color: #011f5b !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    text-transform: none !important;
    box-shadow: 0 2px 4px rgba(1, 31, 91, 0.2) !important;
    transition: all 0.3s ease !important;
}
.primary-btn:hover {
    background-color: #1e40af !important;
    box-shadow: 0 4px 8px rgba(1, 31, 91, 0.3) !important;
    transform: translateY(-1px) !important;
}
.secondary-btn {
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    text-transform: none !important;
    transition: all 0.3s ease !important;
}
.secondary-btn:hover {
    background-color: #e2e8f0 !important;
    border-color: #cbd5e1 !important;
    transform: translateY(-1px) !important;
}
.custom-input {
    border-radius: 8px !important;
    border: 2px solid #e2e8f0 !important;
    transition: all 0.3s ease !important;
}
.custom-input:focus {
    border-color: #011f5b !important;
    box-shadow: 0 0 0 3px rgba(1, 31, 91, 0.1) !important;
}
.custom-number-input {
    border-radius: 8px !important;
    border: 2px solid #e2e8f0 !important;
    transition: all 0.3s ease !important;
}
.custom-number-input:focus {
    border-color: #011f5b !important;
    box-shadow: 0 0 0 3px rgba(1, 31, 91, 0.1) !important;
}
/* Highlight for user's custom model */
.spectral-table-html .user-model-highlight td {
    background-color: #f0fdf4 !important;
    color: #166534 !important;
    font-weight: 700 !important;
    border-top: 2px solid #22c55e;
    border-bottom: 2px solid #22c55e;
    position: relative;
}
.spectral-table-html .user-model-highlight:hover td {
    background-color: #dcfce7 !important;
    transition: all 0.2s ease;
}
/* Enhanced input styles for Add Your Model section */
.enhanced-input,
.enhanced-number-input {
    border-radius: 6px !important;
    border: 1px solid #d1d5db !important;
    background-color: #ffffff !important;
    transition: all 0.2s ease !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
}
.enhanced-input:focus,
.enhanced-number-input:focus {
    border-color: #011f5b !important;
    box-shadow: 0 0 0 2px rgba(1, 31, 91, 0.1) !important;
    outline: none !important;
}
.enhanced-input:hover,
.enhanced-number-input:hover {
    border-color: #9ca3af !important;
}
/* Enhanced button styles */
.enhanced-actions {
    padding: 1.5rem 0 0 0 !important;
    border-top: 1px solid #e2e8f0 !important;
    margin-top: 1rem !important;
}
.enhanced-clear-btn {
    background-color: #ffffff !important;
    color: #64748b !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    text-transform: none !important;
    font-size: 0.95rem !important;
    min-width: 100px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
}
.enhanced-clear-btn:hover {
    background-color: #f8fafc !important;
    border-color: #cbd5e1 !important;
    color: #475569 !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}
.enhanced-run-btn {
    background: #011f5b !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    font-weight: 600 !important;
    text-transform: none !important;
    font-size: 0.95rem !important;
    min-width: 180px !important;
    box-shadow: 0 2px 4px rgba(1, 31, 91, 0.15) !important;
    transition: all 0.2s ease !important;
    border: none !important;
}
.enhanced-run-btn:hover {
    background: #1e40af !important;
    box-shadow: 0 3px 8px rgba(1, 31, 91, 0.2) !important;
}
/* Input label improvements */
.enhanced-input .q-field__label,
.enhanced-number-input .q-field__label {
    font-weight: 500 !important;
    color: #374151 !important;
    font-size: 0.85rem !important;
    margin-bottom: 6px !important;
    letter-spacing: 0.025em !important;
}
/* Number input specific adjustments */
.enhanced-number-input .q-field__control {
    min-height: 44px !important;
}
/* Enhanced Loading Animation Styles */
.enhanced-loading-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 2rem;
    width: 100%;
}
.enhanced-loading-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border-radius: 16px;
    padding: 2.5rem;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1), 0 20px 40px rgba(0, 0, 0, 0.08);
    border: 1px solid rgba(226, 232, 240, 0.8);
    max-width: 500px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
    position: relative;
    overflow: hidden;
}
.enhanced-loading-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(1, 31, 91, 0.03), transparent);
    animation: shimmer 2s infinite;
}
@keyframes shimmer {
    0% { left: -100%; }
    100% { left: 100%; }
}
.enhanced-loading-icon-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    position: relative;
}
.enhanced-loading-icon {
    font-size: 3.5rem !important;
    color: #011f5b !important;
    animation: pulse 2s infinite;
    filter: drop-shadow(0 4px 8px rgba(1, 31, 91, 0.2));
}
@keyframes pulse {
    0%, 100% {
        transform: scale(1);
        opacity: 1;
    }
    50% {
        transform: scale(1.1);
        opacity: 0.8;
    }
}
.enhanced-loading-dots {
    display: flex;
    gap: 0.5rem;
}
.enhanced-loading-dots span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: linear-gradient(135deg, #011f5b, #3b82f6);
    animation: bounce 1.4s infinite ease-in-out both;
}
.enhanced-loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.enhanced-loading-dots span:nth-child(2) { animation-delay: -0.16s; }
.enhanced-loading-dots span:nth-child(3) { animation-delay: 0s; }
@keyframes bounce {
    0%, 80%, 100% {
        transform: scale(0.8);
        opacity: 0.5;
    }
    40% {
        transform: scale(1);
        opacity: 1;
    }
}
.enhanced-loading-text-container {
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
.enhanced-loading-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #011f5b;
    margin: 0;
    animation: fadeInUp 0.6s ease-out;
}
.enhanced-loading-subtitle {
    font-size: 1rem;
    font-weight: 500;
    color: #475569;
    margin: 0;
    animation: fadeInUp 0.6s ease-out 0.2s both;
}
.enhanced-loading-note {
    font-size: 0.875rem;
    font-weight: 400;
    color: #64748b;
    margin: 0;
    animation: fadeInUp 0.6s ease-out 0.4s both;
}
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
.enhanced-loading-progress {
    width: 100%;
    height: 4px;
    background-color: #e2e8f0;
    border-radius: 2px;
    overflow: hidden;
    position: relative;
}
.enhanced-loading-bar {
    height: 100%;
    background: linear-gradient(90deg, #011f5b 0%, #3b82f6 50%, #60a5fa 100%);
    border-radius: 2px;
    animation: progress 2s ease-in-out infinite;
    position: relative;
}
.enhanced-loading-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
    animation: shimmer-bar 1.5s infinite;
}
@keyframes progress {
    0% { width: 0%; }
    50% { width: 70%; }
    100% { width: 100%; }
}
@keyframes shimmer-bar {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
/* Responsive adjustments for loading animation */
@media (max-width: 640px) {
    .enhanced-loading-card {
        padding: 2rem 1.5rem;
        margin: 0 1rem;
    }
    .enhanced-loading-icon {
        font-size: 3rem !important;
    }
    .enhanced-loading-title {
        font-size: 1.25rem;
    }
    .enhanced-loading-subtitle {
        font-size: 0.9rem;
    }
}
'''

# CSS is now added in main.py dashboard route - no need to add here

def toggle_mobile_nav():
    """Toggle mobile navigation menu"""
    ui.run_javascript('''
        const mobileNav = document.querySelector('.mobile-nav');
        if (mobileNav.style.display === 'block') {
            mobileNav.style.display = 'none';
        } else {
            mobileNav.style.display = 'block';
        }
    ''')

def load_llm_data():
    """Load LLM ranking data from CSV file"""
    try:
        # Load the ranking data
        csv_file = os.path.join(PROJECT_ROOT, 'data_llm', 'data_huggingface', 'data_processing', 'huggingface_processed_top100.csv')
        df = pd.read_csv(csv_file)

        # Skip non-numeric rows (like leaderboard names) and find numeric data
        numeric_rows = []
        for i, row in df.iterrows():
            # Check if the first cell after 'benchmark' is numeric
            first_value = str(row.iloc[1]) if len(row) > 1 else ''
            try:
                float(first_value)
                numeric_rows.append(i)
            except (ValueError, TypeError):
                continue

        if not numeric_rows:
            # Fallback: assume first data row is numeric
            numeric_rows = [1] if len(df) > 1 else [0]

        # Use only numeric rows for analysis
        numeric_df = df.iloc[numeric_rows].copy()

        # Get benchmark names (from first column of numeric data, excluding average_score)
        all_benchmarks = numeric_df.iloc[:, 0].tolist()
        benchmark_indices = [i for i, b in enumerate(all_benchmarks) if b != 'average_score']
        benchmarks = [all_benchmarks[i] for i in benchmark_indices]

        # Get model names and scores from numeric data
        models = numeric_df.columns[1:].tolist()  # Column names (skip first column 'benchmark')
        # Only include scores for non-average benchmarks
        scores = numeric_df.iloc[benchmark_indices, 1:].values.T  # Transpose to get model x benchmark scores

        # Convert to float array for calculations
        try:
            scores = scores.astype(float)
        except (ValueError, TypeError):
            logger.warning("Could not convert scores to float, using fallback")
            # Create dummy scores for fallback
            scores = np.random.rand(len(models), len(benchmarks))

        # Try to load additional ranking results from spectral analysis
        spectral_results = load_spectral_results()

        if spectral_results:
            # Use spectral ranking results if available
            logger.info("Using spectral ranking results for model ordering")

            # Sort methods by rank (ascending) to ensure rank 1 comes first
            sorted_methods = sorted(spectral_results.get('methods', []), key=lambda x: x['rank'])

            # Get the ranked model order from sorted spectral results
            ranked_models = [method['name'] for method in sorted_methods]
            # Create mapping from model name to index in original data
            model_to_index = {model: i for i, model in enumerate(models)}

            # Reorder based on spectral ranking with fuzzy matching for truncated names
            ranked_indices = []
            ranked_scores_list = []
            for model in ranked_models:
                idx = None
                if model in model_to_index:
                    # Exact match
                    idx = model_to_index[model]
                elif '...' in model:
                    # Try to match truncated names
                    base_name = model.split('...')[0]
                    # Look for models that start with the base name
                    candidates = [i for i, m in enumerate(models) if m.startswith(base_name)]
                    if candidates:
                        idx = candidates[0]  # Take the first match
                elif len(model) > 10:  # Likely a long model name that might be truncated
                    # Try partial matching
                    candidates = [i for i, m in enumerate(models) if model.startswith(m) or m.startswith(model)]
                    if candidates:
                        idx = candidates[0]

                if idx is not None:
                    ranked_indices.append(idx)
                    ranked_scores_list.append(scores[idx])
                else:
                    logger.warning(f"Could not find data for model: {model}")

            if ranked_scores_list:
                ranked_scores = np.array(ranked_scores_list)
                ranked_avg_scores = np.mean(ranked_scores, axis=1)
                # Update spectral_results with sorted methods for table display
                spectral_results['methods'] = sorted_methods
            else:
                # Fallback to average-based ranking
                avg_scores = np.mean(scores, axis=1)
                ranked_indices = np.argsort(avg_scores)[::-1]
                ranked_scores = scores[ranked_indices]
                ranked_avg_scores = avg_scores[ranked_indices]
        else:
            # Calculate average scores for ranking (fallback)
            logger.info("Using average-based ranking (spectral results not available)")
            avg_scores = np.mean(scores, axis=1)
            ranked_indices = np.argsort(avg_scores)[::-1]  # Sort in descending order
            ranked_scores = scores[ranked_indices]
            ranked_avg_scores = avg_scores[ranked_indices]

        # Create ranked data
        if 'ranked_models' not in locals():
            ranked_models = [models[i] for i in ranked_indices]

        return {
            'benchmarks': benchmarks,
            'models': ranked_models,
            'scores': ranked_scores,
            'avg_scores': ranked_avg_scores,
            'original_df': df,
            'spectral_results': spectral_results
        }
    except Exception as e:
        logger.error(f"Error loading LLM data: {e}")
        return None

def load_spectral_results():
    """Load enhanced spectral ranking results with leaderboard data"""
    try:
        # Try enhanced results first
        enhanced_file = os.path.join(PROJECT_ROOT, 'data_llm', 'data_huggingface', 'data_ranking', 'current', 'huggingface_ranking_result_enhanced.json')
        if os.path.exists(enhanced_file):
            with open(enhanced_file, 'r') as f:
                data = json.load(f)
            logger.info("Loaded enhanced spectral ranking results with leaderboard data")
            return data

        # Fallback to basic ranking results
        basic_file = os.path.join(PROJECT_ROOT, 'data_llm', 'data_huggingface', 'data_ranking', 'current', 'huggingface_ranking_result_basic.json')
        if os.path.exists(basic_file):
            with open(basic_file, 'r') as f:
                data = json.load(f)
            logger.info("Loaded basic spectral ranking results")
            return data

        logger.info("Spectral results file not found, using average-based ranking")
        return None
    except Exception as e:
        logger.error(f"Error loading spectral results: {e}")
        return None

def create_ranking_table(data, highlight_model: str = None):
    """Create ranking table visualization based on spectral ranking results"""
    with ui.element('div').classes('ranking-table'):
        with ui.element('div').classes('ranking-header'):
            # Use a row to align title and button
            with ui.row().style('width: 100%; justify-content: space-between; align-items: center;'):
                # Title part
                with ui.element('div').classes('flex items-center'):
                    ui.html('<span class="material-symbols-outlined ranking-header-icon">leaderboard</span>')
                    # Determine table type and show appropriate title
                    spectral_results = data.get('spectral_results')
                    if spectral_results and 'methods' in spectral_results:
                        has_benchmark_scores = any(method.get('benchmark_scores') for method in spectral_results.get('methods', []))
                        if has_benchmark_scores:
                            is_arena = any(method.get('benchmark_scores', {}).get('creative_writing') is not None
                                         for method in spectral_results.get('methods', []))
                            if is_arena:
                                title_text = 'Arena Spectral Rankings'
                            else:
                                title_text = 'Hugging Face Spectral Rankings'
                        else:
                            title_text = 'LLM Spectral Rankings'
                    else:
                        title_text = 'LLM Spectral Rankings'
                    ui.html(f'<span>{title_text}</span>')

                # Toggle button part
                spectral_results = data.get('spectral_results')
                if spectral_results and 'methods' in spectral_results:
                    ui.button('Spectral Ranking Detail', on_click=lambda: ui.run_javascript(
                        '''
                        const tables = document.querySelectorAll('.spectral-table-html table');
                        tables.forEach(table => {
                            table.classList.toggle('show-details');
                        });
                        '''
                    )).props('flat dense').classes('spectral-detail-button').style('text-transform: none;')

        # Top 3 Legend
        with ui.element('div').classes('top-3-legend'):
            with ui.element('div').classes('legend-item'):
                ui.html('<div class="legend-color first"></div>')
                ui.html('<span>First Place</span>')
            with ui.element('div').classes('legend-item'):
                ui.html('<div class="legend-color second"></div>')
                ui.html('<span>Second Place</span>')
            with ui.element('div').classes('legend-item'):
                ui.html('<div class="legend-color third"></div>')
                ui.html('<span>Third Place</span>')

        with ui.element('div').classes('ranking-content'):
            # Check if spectral results are available
            spectral_results = data.get('spectral_results')
            if spectral_results and 'methods' in spectral_results:
                # Check if methods have benchmark_scores
                has_benchmark_scores = any(method.get('benchmark_scores') for method in spectral_results.get('methods', []))
                if has_benchmark_scores:
                    # Use spectral ranking results with benchmark scores
                    create_spectral_ranking_table(data, spectral_results, highlight_model=highlight_model)
                else:
                    # Fallback to basic ranking table
                    create_arena_ranking_table(spectral_results, is_arena_specific=False)
            else:
                # Fallback to average-based ranking
                create_average_ranking_table(data)

    # Add shared table styles
    ui.add_head_html(f'<style>{TABLE_STYLES}</style>')

def create_html_table(columns, rows, table_id, highlight_model: str = None):
    """Create HTML table with proper rendering of HTML content"""
    # Check if this is the Arena table to apply special layout
    is_arena_table = 'arena-table' in table_id
    table_class = 'arena-table-layout' if is_arena_table else ''

    # Build table header
    header_html = '<thead><tr>'
    for i, col in enumerate(columns):
        align = col.get('align', 'left')
        
        class_list = []
        if col.get('toggleable'):
            class_list.append('toggleable-col')
        if col.get('class'):
            class_list.append(col['class'])

        onclick_attr = ''
        label_html = col["label"]
        
        if col.get('sortable') and col['name'] != 'model':
            class_list.append('sortable-header')
            onclick_attr = f'onclick="sortTable(this, {i}, \'{table_id}\')"'
            # Add sorting icons
            label_html += '''
                <span class="sort-icons">
                    <span class="material-symbols-outlined sort-icon-up">arrow_drop_up</span>
                    <span class="material-symbols-outlined sort-icon-down">arrow_drop_down</span>
                </span>
            '''

        # Handle tooltip
        if col.get('tooltip'):
            label_html = f'''
                <span class="tooltip-container">
                    {label_html}
                    <span class="tooltip-text">{col['tooltip']}</span>
                </span>
            '''

        class_attr = f'class="{" ".join(class_list)}"' if class_list else ''
        header_html += f'<th {class_attr} {onclick_attr} style="{col.get("style", "")} text-align: {align};">{label_html}</th>'
    header_html += '</tr></thead>'

    # Build table body
    body_html = '<tbody>'
    for row in rows:
        row_class = row.get('_row_class', '')
        # Add highlight class for user's model
        if highlight_model and row.get('model', {}).get('original_name') == highlight_model:
            row_class += ' user-model-highlight'

        class_attr = f'class="{row_class.strip()}"' if row_class.strip() else ''
        body_html += f'<tr {class_attr}>'
        for col in columns:
            field = col['name']
            cell_data = row.get(field, '')
            if isinstance(cell_data, dict):
                value = cell_data.get('value', '')
                cell_class = cell_data.get('class', '')
            else:
                value = cell_data
                cell_class = ''

            align = col.get('align', 'left')
            cell_style = f"{col.get('style', '')} text-align: {align};"

            class_list = []
            if field == 'model':
                class_list.append('model-cell')
            elif field == 'rank':
                class_list.append('rank-cell')

            if cell_class:
                class_list.append(cell_class)

            if col.get('toggleable'):
                class_list.append('toggleable-col')

            if col.get('class'):
                class_list.append(col['class'])

            class_attr = f'class="{" ".join(class_list)}"' if class_list else ''

            body_html += f'<td {class_attr} style="{cell_style}">{value}</td>'
        body_html += '</tr>'
    body_html += '</tbody>'

    # Combine into full table
    table_html = f'''
    <table id="{table_id}" class="modern-table spectral-table {table_class}" style="width: 100%; font-size: 0.85em; border-collapse: separate; border-spacing: 0;">
        {header_html}
        {body_html}
    </table>
    '''

    return table_html

def create_spectral_ranking_table(data, spectral_results, highlight_model: str = None):
    """Create table using spectral ranking results with all benchmark scores"""
    is_arena = any(method.get('benchmark_scores', {}).get('creative_writing') is not None
                   for method in spectral_results.get('methods', []))

    # Dynamically set tooltips and column styles based on data source
    if is_arena:
        # Tooltips for Arena table
        spectral_rank_tooltip = 'The model\'s rank calculated using the Spectral Ranking algorithm. This method provides a more robust result by considering pairwise comparisons across 7 virtual benchmarks derived from human preference data (e.g., Creative Writing, Math, Coding).'
        score_rank_tooltip = 'The model\'s rank based on the simple average score across the 7 virtual benchmarks. Used for comparison against the more robust Spectral Rank.'
        # Column definitions for Arena table
        columns = [
            {'name': 'model', 'label': 'Model', 'field': 'model', 'align': 'left', 'style': 'width: 150px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;', 'sortable': True, 'class': 'core-column'},
            {'name': 'rank', 'label': 'Spectral Rank', 'field': 'rank', 'align': 'left', 'sortable': True, 'tooltip': spectral_rank_tooltip, 'class': 'core-column'},
            {'name': 'theta_hat', 'label': 'θ-hat Score', 'field': 'theta_hat', 'align': 'left', 'style': 'width: 90px; min-width: 90px; max-width: 90px;', 'sortable': False, 'toggleable': True, 'tooltip': 'The estimated performance score from the Spectral Ranking algorithm. Higher is better.', 'class': 'core-column'},
            {'name': 'ci_95', 'label': '95% CI', 'field': 'ci_95', 'align': 'left', 'style': 'width: 80px; min-width: 80px; max-width: 80px;', 'sortable': False, 'toggleable': True, 'tooltip': 'The 95% two-sided confidence interval for the rank. For example, an interval of [1, 3] means we are 95% confident the model\'s true rank is between 1 and 3.', 'class': 'core-column'},
            {'name': 'ci_left', 'label': 'Left CI', 'field': 'ci_left', 'align': 'left', 'style': 'width: 70px; min-width: 70px; max-width: 70px;', 'sortable': False, 'toggleable': True, 'tooltip': 'The 95% one-sided confidence interval (lower bound) for the rank. A value of 2 means we are 95% confident the true rank is no better than 2nd place.', 'class': 'core-column'},
            {'name': 'ci_uniform', 'label': 'Uniform CI', 'field': 'ci_uniform', 'align': 'left', 'style': 'width: 80px; min-width: 80px; max-width: 80px;', 'sortable': False, 'toggleable': True, 'tooltip': 'A more conservative, uniform one-sided confidence interval for the rank that holds simultaneously for all models with 95% confidence.', 'class': 'core-column'},
            {'name': 'avg_rank', 'label': 'Score Rank', 'field': 'avg_rank', 'align': 'left', 'sortable': True, 'tooltip': score_rank_tooltip, 'class': 'core-column'},
        ]
        benchmark_columns = [
            {'name': 'creative_writing', 'label': 'Creative Writing', 'field': 'creative_writing', 'align': 'left', 'sortable': True, 'tooltip': 'The model\'s rank in the "Creative Writing" category. This category evaluates the ability to generate original, imaginative, and emotionally resonant content based on human preference votes.'},
            {'name': 'math', 'label': 'Math', 'field': 'math', 'align': 'left', 'sortable': True, 'tooltip': 'The model\'s rank in the "Math" category. This category evaluates the ability to apply mathematical reasoning and problem-solving skills based on human preference votes.'},
            {'name': 'instruction_following', 'label': 'Instruction Following', 'field': 'instruction_following', 'align': 'left', 'sortable': True, 'tooltip': 'The model\'s rank in the "Instruction Following" category. This category evaluates the ability to accurately follow specific and detailed user instructions based on human preference votes.'},
            {'name': 'coding', 'label': 'Coding', 'field': 'coding', 'align': 'left', 'sortable': True, 'tooltip': 'The model\'s rank in the "Coding" category. This category evaluates the ability to understand, generate, and debug code based on human preference votes.'},
            {'name': 'hard_prompt', 'label': 'Hard Prompt', 'field': 'hard_prompt', 'align': 'left', 'sortable': True, 'tooltip': 'The model\'s rank in the "Hard Prompt" category. This category evaluates the ability to handle complex, rigorously designed prompts that require multiple skills, based on human preference votes.'},
            {'name': 'longer_query', 'label': 'Longer Query', 'field': 'longer_query', 'align': 'left', 'sortable': True, 'tooltip': 'The model\'s rank in the "Longer Query" category. This category includes user prompts that are longer than 500 tokens, testing long-context understanding.'},
            {'name': 'multi_turn', 'label': 'Multi-turn', 'field': 'multi_turn', 'align': 'left', 'sortable': True, 'tooltip': 'The model\'s rank in the "Multi-Turn" category. This category evaluates performance in conversational interactions that involve more than one turn.'},
        ]
    else:
        # Tooltips for Hugging Face table
        spectral_rank_tooltip = 'The model\'s rank calculated using the Spectral Ranking algorithm. This method provides a more robust result by considering pairwise comparisons based on scores from 6 key benchmarks: IFEval, BBH, MATH, GPQA, MUSR, and MMLU-Pro.'
        score_rank_tooltip = 'The model\'s rank based on its average score across all benchmarks. Used for comparison against Spectral Rank.'
        # Column definitions for Hugging Face table
        columns = [
            {'name': 'model', 'label': 'Model', 'field': 'model', 'align': 'left', 'style': 'width: 125px; max-width: 125px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;', 'sortable': True, 'class': 'core-column'},
            {'name': 'rank', 'label': 'Spectral Rank', 'field': 'rank', 'align': 'left', 'style': 'width: 70px;', 'sortable': True, 'tooltip': spectral_rank_tooltip, 'class': 'core-column'},
            {'name': 'theta_hat', 'label': 'θ-hat Score', 'field': 'theta_hat', 'align': 'left', 'style': 'width: 80px;', 'sortable': True, 'toggleable': True, 'tooltip': 'The estimated performance score from the Spectral Ranking algorithm. Higher is better.', 'class': 'core-column'},
            {'name': 'ci_95', 'label': '95% CI', 'field': 'ci_95', 'align': 'left', 'style': 'width: 85px;', 'sortable': False, 'toggleable': True, 'tooltip': 'The 95% two-sided confidence interval for the rank. For example, an interval of [1, 3] means we are 95% confident the model\'s true rank is between 1 and 3.', 'class': 'core-column'},
            {'name': 'ci_left', 'label': 'Left CI', 'field': 'ci_left', 'align': 'left', 'style': 'width: 60px;', 'sortable': False, 'toggleable': True, 'tooltip': 'The 95% one-sided confidence interval (lower bound) for the rank. A value of 2 means we are 95% confident the true rank is no better than 2nd place.', 'class': 'core-column'},
            {'name': 'ci_uniform', 'label': 'Uniform CI', 'field': 'ci_uniform', 'align': 'left', 'style': 'width: 75px;', 'sortable': False, 'toggleable': True, 'tooltip': 'A more conservative, uniform one-sided confidence interval for the rank that holds simultaneously for all models with 95% confidence.', 'class': 'core-column'},
            {'name': 'avg_rank', 'label': 'Score Rank', 'field': 'avg_rank', 'align': 'left', 'style': 'width: 70px;', 'sortable': True, 'tooltip': score_rank_tooltip, 'class': 'core-column'},
        ]
        # Hugging Face benchmark score columns
        benchmark_columns = [
            {'name': 'ifeval', 'label': 'IFEval', 'field': 'ifeval', 'align': 'left', 'style': 'width: 70px;', 'sortable': True, 'tooltip': 'Instruction Following Evaluation (IFEval): Assesses the model\'s ability to follow complex and detailed instructions, focusing on precision and adherence to constraints, not creativity.'},
            {'name': 'bbh', 'label': 'BBH', 'field': 'bbh', 'align': 'left', 'style': 'width: 70px;', 'sortable': True, 'tooltip': 'Big-Bench Hard (BBH): A challenging subset of the Big-Bench benchmark, featuring 23 tasks that require significant multi-step reasoning abilities from the language models.'},
            {'name': 'math', 'label': 'MATH', 'field': 'math', 'align': 'left', 'style': 'width: 70px;', 'sortable': True, 'tooltip': 'A benchmark consisting of 12,500 challenging competition mathematics problems from high school level contests, designed to test mathematical problem-solving and reasoning.'},
            {'name': 'gpqa', 'label': 'GPQA', 'field': 'gpqa', 'align': 'left', 'style': 'width: 70px;', 'sortable': True, 'tooltip': 'Graduate-Level Google-Proof Q&A (GPQA): A difficult dataset of questions written by domain experts that are hard to find answers for using search engines, testing deep domain knowledge.'},
            {'name': 'musr', 'label': 'MUSR', 'field': 'musr', 'align': 'left', 'style': 'width: 70px;', 'sortable': True, 'tooltip': 'Multi-Step Reasoning (MuSR): Evaluates the model\'s ability to perform complex, multi-step reasoning by solving problems that require chaining together facts and inferences.'},
            {'name': 'mmlu_pro', 'label': 'MMLU-Pro', 'field': 'mmlu_pro', 'align': 'left', 'style': 'width: 70px;', 'sortable': True, 'tooltip': 'An advanced version of the MMLU benchmark that features more challenging questions requiring deeper knowledge and reasoning, curated by subject matter experts.'},
            {'name': 'average', 'label': 'Average', 'field': 'average', 'align': 'left', 'style': 'width: 70px; font-weight: bold;', 'sortable': True, 'tooltip': 'The arithmetic mean of the scores from all the benchmarks displayed, providing an overall performance indicator.'},
        ]

    columns.extend(benchmark_columns)

    # Define benchmark_names for later use
    benchmark_names = [col['name'] for col in benchmark_columns] if is_arena else []

    # Calculate ranks for Arena data
    if is_arena:
        benchmark_ranks = {}
        for benchmark in benchmark_names:
            scores_with_models = []
            for method in spectral_results.get('methods', []):
                model_name = method['name']
                if 'benchmark_scores' in method and benchmark in method['benchmark_scores']:
                    score = float(method['benchmark_scores'][benchmark])
                    scores_with_models.append({'model': model_name, 'score': score})
            sorted_scores = sorted(scores_with_models, key=lambda x: x['score'], reverse=True)
            ranks = {item['model']: i + 1 for i, item in enumerate(sorted_scores)}
            benchmark_ranks[benchmark] = ranks

    # Prepare table data using spectral results
    # Sort methods by rank (ascending) to ensure rank 1 comes first in the table
    table_data = []
    methods = sorted(spectral_results['methods'], key=lambda x: x['rank'])

    # Calculate average rank based on average_score
    avg_score_ranks = {}
    sorted_by_avg = sorted(methods, key=lambda x: float(x.get('benchmark_scores', {}).get('average_score', 0)), reverse=True)
    for i, method in enumerate(sorted_by_avg):
        avg_score_ranks[method['name']] = i + 1

    # Calculate top 3 for each column (except model)
    column_top3 = {}
    all_columns = [col['name'] for col in columns] + [col['name'] for col in benchmark_columns]

    for col_name in all_columns:
        if col_name == 'model':
            continue

        # Collect values for this column
        col_values = []
        for method in methods:
            if col_name == 'rank':
                value = method['rank']
            elif col_name == 'avg_rank':
                value = avg_score_ranks.get(method['name'], float('inf'))
            elif col_name == 'theta_hat':
                value = method['theta_hat']
            elif col_name in ['ci_95', 'ci_left', 'ci_uniform']:
                # For CI columns, we can't easily rank them, so skip
                continue
            elif col_name in benchmark_names:
                # For benchmark ranks (Arena)
                value = benchmark_ranks.get(col_name, {}).get(method['name'], float('inf'))
            else:
                # For benchmark scores (Hugging Face)
                benchmark_scores = method.get('benchmark_scores', {})
                # Use the same mapping as in data population
                benchmark_mappings = {
                    'ifeval': 'ifeval',
                    'bbh': 'bbh',
                    'math': 'math',
                    'gpqa': 'gpqa',
                    'musr': 'musr',
                    'mmlu_pro': 'mmlu_pro',
                    'average': 'average_score'
                }
                data_name = benchmark_mappings.get(col_name, col_name)
                value_str = benchmark_scores.get(data_name, 'N/A')
                if value_str != 'N/A':
                    try:
                        value = float(value_str)
                    except (ValueError, TypeError):
                        value = float('inf')
                else:
                    value = float('inf')

            col_values.append({'model': method['name'], 'value': value})

        # Sort and get top 3 (lower rank/score is better for rank columns, higher score is better for score columns)
        if col_name in ['rank', 'avg_rank'] or (is_arena and col_name in benchmark_names):
            # Lower values are better for rank columns
            sorted_values = sorted(col_values, key=lambda x: x['value'])
        else:
            # Higher values are better for score columns
            sorted_values = sorted(col_values, key=lambda x: x['value'], reverse=True)

        top3_models = [item['model'] for item in sorted_values[:3]]
        column_top3[col_name] = {
            'first': top3_models[0] if len(top3_models) > 0 else None,
            'second': top3_models[1] if len(top3_models) > 1 else None,
            'third': top3_models[2] if len(top3_models) > 2 else None
        }

    for method in methods:
        model_name = method['name']
        rank = method['rank']
        theta_hat = method['theta_hat']
        ci_two_left = method['ci_two_sided'][0]
        ci_two_right = method['ci_two_sided'][1]
        ci_left = method['ci_left']
        ci_uniform_left = method['ci_uniform_left']

        # Get benchmark scores and model URL from enhanced method data
        benchmark_scores = method.get('benchmark_scores', {})
        model_url = method.get('model_url')

        # Create clickable model name if URL is available
        model_display = model_name
        if model_url:
            model_display = f'<a href="{model_url}" target="_blank" style="color: #2563eb; text-decoration: underline;">{model_name}</a>'

        # Create row data with cell-level CSS classes for top 3
        row = {}

        # Model column (no highlighting)
        row['model'] = {'value': model_display, 'class': '', 'original_name': model_name}

        # Rank column
        rank_class = ''
        if column_top3.get('rank', {}).get('first') == model_name:
            rank_class = 'first-place-cell'
        elif column_top3.get('rank', {}).get('second') == model_name:
            rank_class = 'second-place-cell'
        elif column_top3.get('rank', {}).get('third') == model_name:
            rank_class = 'third-place-cell'
        row['rank'] = {'value': rank, 'class': rank_class}

        # Avg rank column
        avg_rank_class = ''
        if column_top3.get('avg_rank', {}).get('first') == model_name:
            avg_rank_class = 'first-place-cell'
        elif column_top3.get('avg_rank', {}).get('second') == model_name:
            avg_rank_class = 'second-place-cell'
        elif column_top3.get('avg_rank', {}).get('third') == model_name:
            avg_rank_class = 'third-place-cell'
        row['avg_rank'] = {'value': avg_score_ranks.get(model_name, 'N/A'), 'class': avg_rank_class}

        # Theta hat column
        theta_class = ''
        if column_top3.get('theta_hat', {}).get('first') == model_name:
            theta_class = 'first-place-cell'
        elif column_top3.get('theta_hat', {}).get('second') == model_name:
            theta_class = 'second-place-cell'
        elif column_top3.get('theta_hat', {}).get('third') == model_name:
            theta_class = 'third-place-cell'
        row['theta_hat'] = {'value': f'{theta_hat:.4f}', 'class': theta_class}

        # CI columns (no highlighting)
        row['ci_95'] = {'value': f'[{ci_two_left}, {ci_two_right}]', 'class': ''}
        row['ci_left'] = {'value': f'≤{ci_left}', 'class': ''}
        row['ci_uniform'] = {'value': f'≤{ci_uniform_left}', 'class': ''}

        # Populate benchmark data
        if is_arena:
            # Add ranks for Arena
            for benchmark in benchmark_names:
                benchmark_value = benchmark_ranks.get(benchmark, {}).get(model_name, 'N/A')
                benchmark_class = ''
                if column_top3.get(benchmark, {}).get('first') == model_name:
                    benchmark_class = 'first-place-cell'
                elif column_top3.get(benchmark, {}).get('second') == model_name:
                    benchmark_class = 'second-place-cell'
                elif column_top3.get(benchmark, {}).get('third') == model_name:
                    benchmark_class = 'third-place-cell'
                row[benchmark] = {'value': benchmark_value, 'class': benchmark_class}
        else:
            # Add scores for Hugging Face
            benchmark_mappings = {
                'ifeval': 'ifeval',
                'bbh': 'bbh',
                'math': 'math',
                'gpqa': 'gpqa',
                'musr': 'musr',
                'mmlu_pro': 'mmlu_pro',
                'average': 'average_score'
            }

            for display_name, data_name in benchmark_mappings.items():
                value = benchmark_scores.get(data_name)
                if value is not None:
                    formatted_value = f"{float(value):.2f}"
                else:
                    formatted_value = 'N/A'

                benchmark_class = ''
                if column_top3.get(display_name, {}).get('first') == model_name:
                    benchmark_class = 'first-place-cell'
                elif column_top3.get(display_name, {}).get('second') == model_name:
                    benchmark_class = 'second-place-cell'
                elif column_top3.get(display_name, {}).get('third') == model_name:
                    benchmark_class = 'third-place-cell'

                row[display_name] = {'value': formatted_value, 'class': benchmark_class}

        table_data.append(row)

    # Create scrollable container for the table with fixed header
    with ui.element('div').style('max-height: 600px; overflow: auto; border: 1px solid #e0e0e0; border-radius: 8px; position: relative;'):
        # Create custom HTML table with proper HTML rendering
        table_html = create_html_table(columns, table_data, table_id='huggingface-table' if not is_arena else 'arena-table', highlight_model=highlight_model)
        ui.html(table_html).classes('spectral-table-html')

    # Add shared table styles
    ui.add_head_html(f'<style>{TABLE_STYLES}</style>')

def create_arena_ranking_table(spectral_results, is_arena_specific=False):
    """Create table for Arena spectral ranking results (no benchmark scores)"""
    # Create table with NiceGUI
    columns = [
        {'name': 'model', 'label': 'Model', 'field': 'model', 'align': 'left', 'style': 'width: 300px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;', 'sortable': True},
        {'name': 'rank', 'label': 'Spectral Rank', 'field': 'rank', 'align': 'left', 'style': 'width: 60px;', 'sortable': True, 'tooltip': 'The model\'s rank as determined by the Spectral Ranking algorithm, which provides a more robust result by considering pairwise comparisons from user preferences in head-to-head battles.'},
        {'name': 'theta_hat', 'label': 'θ-hat Score', 'field': 'theta_hat', 'align': 'left', 'style': 'width: 100px;', 'sortable': True, 'toggleable': True, 'tooltip': 'The estimated performance score from the Spectral Ranking algorithm. Higher is better.'},
        {'name': 'ci_95', 'label': '95% CI', 'field': 'ci_95', 'align': 'left', 'style': 'width: 120px;', 'sortable': False, 'toggleable': True, 'tooltip': 'The 95% two-sided confidence interval for the rank. For example, an interval of [1, 3] means we are 95% confident the model\'s true rank is between 1 and 3.'},
        {'name': 'ci_left', 'label': 'Left CI', 'field': 'ci_left', 'align': 'left', 'style': 'width: 80px;', 'sortable': False, 'toggleable': True, 'tooltip': 'The 95% one-sided confidence interval (lower bound) for the rank. A value of 2 means we are 95% confident the true rank is no better than 2nd place.'},
        {'name': 'ci_uniform', 'label': 'Uniform CI', 'field': 'ci_uniform', 'align': 'left', 'style': 'width: 90px;', 'sortable': False, 'toggleable': True, 'tooltip': 'A more conservative, uniform one-sided confidence interval for the rank that holds simultaneously for all models with 95% confidence.'},
    ]

    # Prepare table data using spectral results
    # Sort methods by rank (ascending) to ensure rank 1 comes first in the table
    table_data = []
    methods = sorted(spectral_results['methods'], key=lambda x: x['rank'])

    # Calculate top 3 for each column (except model)
    column_top3 = {}
    all_columns = [col['name'] for col in columns]

    for col_name in all_columns:
        if col_name == 'model':
            continue

        # Collect values for this column
        col_values = []
        for method in methods:
            if col_name == 'rank':
                value = method['rank']
            elif col_name == 'theta_hat':
                value = method['theta_hat']
            elif col_name in ['ci_95', 'ci_left', 'ci_uniform']:
                # For CI columns, we can't easily rank them, so skip
                continue

            col_values.append({'model': method['name'], 'value': value})

        # Sort and get top 3 (lower rank is better for rank column, higher theta_hat is better)
        if col_name == 'rank':
            # Lower values are better for rank column
            sorted_values = sorted(col_values, key=lambda x: x['value'])
        else:
            # Higher values are better for theta_hat
            sorted_values = sorted(col_values, key=lambda x: x['value'], reverse=True)

        top3_models = [item['model'] for item in sorted_values[:3]]
        column_top3[col_name] = {
            'first': top3_models[0] if len(top3_models) > 0 else None,
            'second': top3_models[1] if len(top3_models) > 1 else None,
            'third': top3_models[2] if len(top3_models) > 2 else None
        }

    for method in methods:
        model_name = method['name']
        rank = method['rank']
        theta_hat = method['theta_hat']
        ci_two_left = method['ci_two_sided'][0]
        ci_two_right = method['ci_two_sided'][1]
        ci_left = method['ci_left']
        ci_uniform_left = method['ci_uniform_left']

        # Create row data with cell-level CSS classes for top 3
        row = {}

        # Model column (no highlighting)
        row['model'] = {'value': model_name, 'class': ''}

        # Rank column
        rank_class = ''
        if column_top3.get('rank', {}).get('first') == model_name:
            rank_class = 'first-place-cell'
        elif column_top3.get('rank', {}).get('second') == model_name:
            rank_class = 'second-place-cell'
        elif column_top3.get('rank', {}).get('third') == model_name:
            rank_class = 'third-place-cell'
        row['rank'] = {'value': rank, 'class': rank_class}

        # Theta hat column
        theta_class = ''
        if column_top3.get('theta_hat', {}).get('first') == model_name:
            theta_class = 'first-place-cell'
        elif column_top3.get('theta_hat', {}).get('second') == model_name:
            theta_class = 'second-place-cell'
        elif column_top3.get('theta_hat', {}).get('third') == model_name:
            theta_class = 'third-place-cell'
        row['theta_hat'] = {'value': f'{theta_hat:.4f}', 'class': theta_class}

        # CI columns (no highlighting)
        row['ci_95'] = {'value': f'[{ci_two_left:.2f}, {ci_two_right:.2f}]', 'class': ''}
        row['ci_left'] = {'value': f'≤{ci_left:.2f}', 'class': ''}
        row['ci_uniform'] = {'value': f'≤{ci_uniform_left:.2f}', 'class': ''}

        table_data.append(row)

    # Create scrollable container for the table with fixed header
    with ui.element('div').style('max-height: 600px; overflow: auto; border: 1px solid #e0e0e0; border-radius: 8px; position: relative;'):
        # Create custom HTML table with proper HTML rendering
        table_html = create_html_table(columns, table_data, table_id='arena-table')
        ui.html(table_html).classes('spectral-table-html')

    # Add CSS for the HTML table
    ui.add_head_html(f'<style>{TABLE_STYLES}</style>')

def create_average_ranking_table(data):
    """Create table using average-based ranking (fallback)"""
    # Create table with NiceGUI
    columns = [
        {'name': 'model', 'label': 'Model', 'field': 'model', 'align': 'left', 'sortable': True},
        {'name': 'rank', 'label': 'Rank', 'field': 'rank', 'align': 'left', 'sortable': True},
        {'name': 'avg_rank', 'label': 'Score Rank', 'field': 'avg_rank', 'align': 'left', 'sortable': True},
        {'name': 'avg_score', 'label': 'Avg Score', 'field': 'avg_score', 'align': 'left', 'sortable': True},
    ]

    # Add benchmark columns
    for benchmark in data['benchmarks']:
        columns.append({
            'name': benchmark,
            'label': benchmark.upper(),
            'field': benchmark,
            'align': 'left',
            'sortable': True
        })

    # Prepare table data
    table_data = []
    for i, (model, avg_score, scores) in enumerate(zip(data['models'][:20], data['avg_scores'][:20], data['scores'][:20])):
        row = {
            'model': model,
            'rank': i + 1,
            'avg_rank': i + 1,  # Same as rank since we're already sorted by average
            'avg_score': f'{avg_score:.2f}'
        }
        for j, benchmark in enumerate(data['benchmarks']):
            row[benchmark] = f'{scores[j]:.2f}'
        table_data.append(row)

    ui.table(columns=columns, rows=table_data).classes('modern-table').style('width: 100%')

def create_performance_chart(data):
    """Create performance comparison chart"""
    with ui.element('div').classes('chart-container'):
        with ui.element('div').classes('chart-title'):
            ui.html('<span class="material-symbols-outlined chart-title-icon">bar_chart</span>')
            ui.html('<span>Top 10 LLM Performance Comparison</span>')

        # Create bar chart for top 10 models
        top_10_models = data['models'][:10]
        top_10_scores = data['scores'][:10]
        benchmarks = data['benchmarks']

        fig = go.Figure()

        for i, benchmark in enumerate(benchmarks):
            fig.add_trace(go.Bar(
                name=benchmark.upper(),
                x=top_10_models,
                y=[scores[i] for scores in top_10_scores],
                marker_color=[
                    '#011f5b', '#1e40af', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd'
                ][i % 6]
            ))

        fig.update_layout(
            barmode='group',
            xaxis_title='LLM Models',
            yaxis_title='Performance Score',
            font=dict(family='Inter', size=12),
            plot_bgcolor='rgba(255,255,255,0.9)',
            paper_bgcolor='rgba(255,255,255,0.9)',
            height=500,
            margin=dict(l=50, r=50, t=50, b=100),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )

        fig.update_xaxes(tickangle=45)

        ui.plotly(fig).classes('plot-container')

def create_benchmark_radar_chart(data):
    """Create radar chart for benchmark comparison"""
    with ui.element('div').classes('chart-container'):
        with ui.element('div').classes('chart-title'):
            ui.html('<span class="material-symbols-outlined chart-title-icon">radar</span>')
            ui.html('<span>Top 5 LLM Benchmark Performance Radar</span>')

        # Get top 5 models
        top_5_models = data['models'][:5]
        top_5_scores = data['scores'][:5]
        benchmarks = data['benchmarks']

        fig = go.Figure()

        colors = ['#011f5b', '#1e40af', '#2563eb', '#3b82f6', '#60a5fa']

        for i, (model, scores) in enumerate(zip(top_5_models, top_5_scores)):
            # Normalize scores to 0-100 scale for better visualization
            normalized_scores = [score for score in scores]

            fig.add_trace(go.Scatterpolar(
                r=normalized_scores + [normalized_scores[0]],  # Close the polygon
                theta=benchmarks + [benchmarks[0]],  # Close the polygon
                fill='toself',
                name=model,
                line_color=colors[i],
                fillcolor=f'rgba{tuple(int(colors[i][1:][j:j+2], 16) for j in (0, 2, 4)) + (0.3,)}'
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            font=dict(family='Inter', size=12),
            plot_bgcolor='rgba(255,255,255,0.9)',
            paper_bgcolor='rgba(255,255,255,0.9)',
            height=500,
            margin=dict(l=50, r=50, t=50, b=50),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.2,
                xanchor='center',
                x=0.5
            )
        )

        ui.plotly(fig).classes('plot-container')

def create_metrics_overview(data, is_arena_mode=False):
    """Create metrics overview cards"""
    with ui.element('div').style('display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin: 2rem 0;'):

        # Total models in ranking
        total_models = len(data["models"])
        with ui.element('div').classes('metric-card'):
            ui.html(f'<div class="metric-value">{total_models}</div>')
            ui.html('<div class="metric-label">Ranked Models</div>')

        # Benchmarks
        benchmark_count = len(data["benchmarks"])
        with ui.element('div').classes('metric-card'):
            ui.html(f'<div class="metric-value">{benchmark_count}</div>')
            if is_arena_mode:
                ui.html('<div class="metric-label">Task Categories</div>')
            else:
                ui.html('<div class="metric-label">Benchmarks</div>')

        # Ranking method & Top Model
        spectral_results = data.get('spectral_results')
        if spectral_results and 'methods' in spectral_results and spectral_results['methods']:
            top_model_name = spectral_results['methods'][0].get('name', 'N/A')
        else:
            top_model_name = data['models'][0] if data['models'] else 'N/A'

        with ui.element('div').classes('metric-card'):
            ui.html(f'<div class="metric-value" style="font-size: 1.5rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{top_model_name}</div>')
            ui.html('<div class="metric-label">Top Ranked Model</div>')

        # Data Source
        if is_arena_mode:
            source_name = "LMSYS Arena"
            source_url = "https://lmarena.ai/leaderboard/"
        else:
            source_name = "Hugging Face"
            source_url = "https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard"

        with ui.element('div').classes('metric-card'):
            ui.html(f'<a href="{source_url}" target="_blank" class="metric-value" style="font-size: 1.5rem; text-decoration: underline; color: var(--primary-700);">{source_name}</a>')
            ui.html('<div class="metric-label">Data Source</div>')

def load_arena_data():
    """Load Arena ranking data from CSV file"""
    try:
        # Load the ranking data (for spectral results)
        csv_file = os.path.join(PROJECT_ROOT, 'data_llm', 'data_arena', 'data_ranking', 'current', 'ranking_results.csv')
        df = pd.read_csv(csv_file)

        # Load benchmark scores from the full ranking file
        benchmark_file = os.path.join(PROJECT_ROOT, 'data_llm', 'data_arena', 'data_processing', 'arena_ranking_full.csv')
        benchmark_df = pd.read_csv(benchmark_file)

        # Extract benchmark names and model names
        benchmarks = benchmark_df['virtual_benchmark'].tolist()
        model_names = benchmark_df.columns[1:].tolist()  # Skip 'virtual_benchmark' column

        # Create benchmark scores matrix (models x benchmarks)
        scores = benchmark_df.iloc[:, 1:].values.T  # Transpose to get model x benchmark

        # Convert to float
        try:
            scores = scores.astype(float)
        except (ValueError, TypeError):
            logger.warning("Could not convert benchmark scores to float")
            scores = np.zeros((len(model_names), len(benchmarks)))

        # Try to load additional ranking results from spectral analysis
        spectral_results = load_spectral_results(arena=True)

        if spectral_results:
            logger.info("Using Arena spectral ranking results for model ordering")

            # Sort methods by rank (ascending) to ensure rank 1 comes first
            sorted_methods = sorted(spectral_results.get('methods', []), key=lambda x: x['rank'])

            # Get the ranked model order from sorted spectral results
            ranked_models = [method['name'] for method in sorted_methods]

            # Create mapping from model name to index in benchmark data
            model_to_index = {model: i for i, model in enumerate(model_names)}

            # Reorder based on spectral ranking with fuzzy matching
            ranked_indices = []
            ranked_scores_list = []
            for model in ranked_models:
                idx = None
                if model in model_to_index:
                    # Exact match
                    idx = model_to_index[model]
                elif '...' in model:
                    # Try to match truncated names
                    base_name = model.split('...')[0]
                    candidates = [i for i, m in enumerate(model_names) if m.startswith(base_name)]
                    if candidates:
                        idx = candidates[0]
                elif len(model) > 10:  # Likely a long model name that might be truncated
                    candidates = [i for i, m in enumerate(model_names) if model.startswith(m) or m.startswith(model)]
                    if candidates:
                        idx = candidates[0]

                if idx is not None:
                    ranked_indices.append(idx)
                    ranked_scores_list.append(scores[idx])
                else:
                    logger.warning(f"Could not find data for model: {model}")

            if ranked_scores_list:
                ranked_scores = np.array(ranked_scores_list)
                ranked_avg_scores = np.mean(ranked_scores, axis=1)
                # Update spectral_results with sorted methods
                spectral_results['methods'] = sorted_methods
            else:
                # Fallback to average-based ranking
                avg_scores = np.mean(scores, axis=1)
                ranked_indices = np.argsort(avg_scores)[::-1]  # Sort in descending order
                ranked_scores = scores[ranked_indices]
                ranked_avg_scores = avg_scores[ranked_indices]
        else:
            # Fallback to average-based ranking
            logger.info("Using average-based ranking (Arena spectral results not available)")
            avg_scores = np.mean(scores, axis=1)
            ranked_indices = np.argsort(avg_scores)[::-1]  # Sort in descending order
            ranked_scores = scores[ranked_indices]
            ranked_avg_scores = avg_scores[ranked_indices]

        # Create ranked data
        if 'ranked_models' not in locals():
            ranked_models = [model_names[i] for i in ranked_indices]

        # Prepare benchmark scores for spectral results (if available)
        if spectral_results and 'methods' in spectral_results:
            # Map benchmark names to table field names
            benchmark_mapping = {
                'creative_writing_bt_prob': 'creative_writing',
                'math_bt_prob': 'math',
                'instruction_following_bt_prob': 'instruction_following',
                'coding_bt_prob': 'coding',
                'hard_prompt_bt_prob': 'hard_prompt',
                'longer_query_bt_prob': 'longer_query',
                'multi_turn_bt_prob': 'multi_turn'
            }

            for i, method in enumerate(spectral_results['methods']):
                if i < len(ranked_scores):
                    method['benchmark_scores'] = {}
                    for j, benchmark in enumerate(benchmarks):
                        # Map to table field name
                        table_field = benchmark_mapping.get(benchmark, benchmark)
                        method['benchmark_scores'][table_field] = ranked_scores[i][j]
                    # Add average score
                    method['benchmark_scores']['average_score'] = ranked_avg_scores[i]

        data = {
            'benchmarks': [b.replace('_bt_prob', '').replace('_', ' ').title() for b in benchmarks],
            'models': ranked_models,
            'scores': ranked_scores,
            'avg_scores': ranked_avg_scores,
            'original_df': df,
            'spectral_results': spectral_results
        }

        return data
    except Exception as e:
        logger.error(f"Error loading Arena data: {e}")
        return None

def load_spectral_results(arena=False):
    """Load enhanced spectral ranking results with leaderboard data"""
    try:
        if arena:
            # Try enhanced results first for Arena
            enhanced_file = os.path.join(PROJECT_ROOT, 'data_llm', 'data_arena', 'data_ranking', 'current', 'arena_ranking_result_enhanced.json')
            if os.path.exists(enhanced_file):
                with open(enhanced_file, 'r') as f:
                    data = json.load(f)
                logger.info("Loaded enhanced Arena spectral ranking results")
                return data

            # Fallback to basic ranking results for Arena
            basic_file = os.path.join(PROJECT_ROOT, 'data_llm', 'data_arena', 'data_ranking', 'current', 'arena_ranking_result_basic.json')
            if os.path.exists(basic_file):
                with open(basic_file, 'r') as f:
                    data = json.load(f)
                logger.info("Loaded basic Arena spectral ranking results")
                return data
        else:
            # Original Hugging Face loading logic
            # Try enhanced results first
            enhanced_file = os.path.join(PROJECT_ROOT, 'data_llm', 'data_huggingface', 'data_ranking', 'current', 'huggingface_ranking_result_enhanced.json')
            if os.path.exists(enhanced_file):
                with open(enhanced_file, 'r') as f:
                    data = json.load(f)
                logger.info("Loaded enhanced spectral ranking results with leaderboard data")
                return data

            # Fallback to basic ranking results
            basic_file = os.path.join(PROJECT_ROOT, 'data_llm', 'data_huggingface', 'data_ranking', 'current', 'huggingface_ranking_result_basic.json')
            if os.path.exists(basic_file):
                with open(basic_file, 'r') as f:
                    data = json.load(f)
                logger.info("Loaded basic spectral ranking results")
                return data

        logger.info("Spectral results file not found, using average-based ranking")
        return None
    except Exception as e:
        logger.error(f"Error loading spectral results: {e}")
        return None

def create_dashboard_content():
    """Create the main dashboard content"""
    # Hero Section
    with ui.element('section').classes('hero-section'):
        with ui.element('div').classes('hero-content'):
            ui.html('''
                <div class="hero-badge" onclick="document.querySelector('.mode-selection-section').scrollIntoView({behavior: 'smooth'});" style="cursor: pointer; transition: opacity 0.3s ease;">
                    <span class="material-symbols-outlined">analytics</span>
                    LLM Performance Dashboard
                </div>
                <h1 class="hero-title">Large Language Model Rankings</h1>
                <p class="hero-subtitle">
                    Comprehensive performance analysis of top 100 LLM models across 6 critical benchmarks.
                    Discover which models excel in instruction following, reasoning, mathematics, and more.
                </p>
            ''')

            # Feature highlights
            with ui.element('div').classes('hero-features'):
                with ui.element('div').classes('hero-feature'):
                    ui.html('<span class="material-symbols-outlined hero-feature-icon">psychology</span>')
                    ui.html('<h3 class="hero-feature-title">Instruction Following</h3>')
                    ui.html('<p class="hero-feature-description">Models evaluated on their ability to follow complex, precise instructions across multiple steps and formats.</p>')

                with ui.element('div').classes('hero-feature'):
                    ui.html('<span class="material-symbols-outlined hero-feature-icon">calculate</span>')
                    ui.html('<h3 class="hero-feature-title">Mathematical Reasoning</h3>')
                    ui.html('<p class="hero-feature-description">Advanced mathematical problem-solving capabilities tested across algebra, geometry, and calculus.</p>')

                with ui.element('div').classes('hero-feature'):
                    ui.html('<span class="material-symbols-outlined hero-feature-icon">school</span>')
                    ui.html('<h3 class="hero-feature-title">Knowledge & Reasoning</h3>')
                    ui.html('<p class="hero-feature-description">Comprehensive evaluation of factual knowledge and logical reasoning across multiple domains.</p>')

    # Mode Selection Cards
    with ui.element('section').classes('mode-selection-section').style('width: 100%; max-width: 1400px; margin: 4rem auto 1rem; padding: 0 2rem;'):
        with ui.element('div').style('display: flex; gap: 2rem; justify-content: center; flex-wrap: wrap;'):

            # LMSYS Arena Mode Card
            with ui.element('div').classes('mode-card active').props('id="arena-mode-card"') as arena_mode_card:
                ui.html('''
                    <div class="card-content">
                        <div class="card-icon-wrapper">⚔️</div>
                        <h3 class="card-title">LMSYS Arena Leaderboard</h3>
                        <p class="card-description">
                            Analyzes crowdsourced human preference data from real-world user interactions. Ranks models based on head-to-head battles, providing insights into practical usability and user satisfaction.
                        </p>
                        <ul class="card-features">
                            <li><span class="material-symbols-outlined">groups</span> Human Preference Data</li>
                            <li><span class="material-symbols-outlined">compare_arrows</span> Head-to-Head Battles</li>
                            <li><span class="material-symbols-outlined">psychology_alt</span> Real-World Performance</li>
                        </ul>
                    </div>
                ''')

            # Hugging Face Mode Card
            with ui.element('div').classes('mode-card inactive').props('id="huggingface-mode-card"') as huggingface_mode_card:
                ui.html('''
                    <div class="card-content">
                        <div class="card-icon-wrapper">🤗</div>
                        <h3 class="card-title">Hugging Face Leaderboard</h3>
                        <p class="card-description">
                            Evaluates models on a suite of standardized academic benchmarks. Ranks models based on performance in areas like reasoning, knowledge, and instruction following.
                        </p>
                        <ul class="card-features">
                            <li><span class="material-symbols-outlined">functions</span> 6 Core Benchmarks</li>
                            <li><span class="material-symbols-outlined">smart_toy</span> Automated Evaluation</li>
                            <li><span class="material-symbols-outlined">workspace_premium</span> Top 100 Models</li>
                        </ul>
                    </div>
                ''')

    # Load initial data
    huggingface_data = load_llm_data()
    arena_data = load_arena_data()

    # Arena Content Section (initially visible)
    arena_section = ui.element('div').style('width: 100%; display: block;').props('id="arena-content"')
    with arena_section:
        if arena_data:
            create_arena_content(arena_data)
        else:
            ui.notify('Failed to load Arena ranking data', type='error')

    # Hugging Face Content Section (initially hidden)
    huggingface_section = ui.element('div').style('width: 100%; display: none;').props('id="huggingface-content"')
    with huggingface_section:
        if huggingface_data:
            create_huggingface_content(huggingface_data)
        else:
            ui.notify('Failed to load Hugging Face ranking data', type='error')

    # Mode switching functions
    def switch_to_huggingface():
        # Show Hugging Face content, hide Arena content
        ui.run_javascript('document.getElementById("huggingface-content").style.display = "block";')
        ui.run_javascript('document.getElementById("arena-content").style.display = "none";')

        # Update card styles
        ui.run_javascript('''
            const hfCard = document.getElementById("huggingface-mode-card");
            const arenaCard = document.getElementById("arena-mode-card");
            hfCard.classList.add("active");
            hfCard.classList.remove("inactive");
            arenaCard.classList.add("inactive");
            arenaCard.classList.remove("active");
        ''')

    def switch_to_arena():
        # Show Arena content, hide Hugging Face content
        ui.run_javascript('document.getElementById("huggingface-content").style.display = "none";')
        ui.run_javascript('document.getElementById("arena-content").style.display = "block";')

        # Update card styles
        ui.run_javascript('''
            const hfCard = document.getElementById("huggingface-mode-card");
            const arenaCard = document.getElementById("arena-mode-card");
            arenaCard.classList.add("active");
            arenaCard.classList.remove("inactive");
            hfCard.classList.add("inactive");
            hfCard.classList.remove("active");
        ''')

    # Bind click events
    huggingface_mode_card.on('click', switch_to_huggingface)
    arena_mode_card.on('click', switch_to_arena)

def create_huggingface_content(data):
    """Create content for Hugging Face mode"""
    # Metrics Overview
    with ui.element('section').style('width: 100%; max-width: 1400px; margin: 0 auto; padding: 0 2rem;'):
        ui.html('<h2 class="section-title">Hugging Face Overview</h2>')
        create_metrics_overview(data, is_arena_mode=False)

    # Rankings Table
    with ui.element('section').style('width: 100%; max-width: 1400px; margin: 0 auto; padding: 0 2rem;'):
        # Determine the number of models being displayed
        spectral_results = data.get('spectral_results')
        if spectral_results and 'methods' in spectral_results:
            display_count = len(spectral_results['methods'])
        else:
            display_count = min(20, len(data.get('models', [])))

        ui.html(f'<h2 class="section-title">Top {display_count} Hugging Face LLM Rankings</h2>')
        create_ranking_table(data)

    # Custom model ranking section
    with ui.element('section').style('width: 100%; max-width: 1400px; margin: 2rem auto; padding: 0 2rem;'):
        ui.html('<h2 class="section-title">Compare With Your Model</h2>')
        
        with ui.card().classes('compare-card w-full'):
            with ui.card_section():
                with ui.element('div').classes('compare-header'):
                    ui.html('<div class="compare-icon"><span class="material-symbols-outlined">tune</span></div>')
                    ui.html('<div><div class="card-title" style="margin:0;">Add Your Model</div><div class="helper-text">Enter a name and six benchmark scores (0-100). We will re-run spectral ranking against the current Top 100.</div></div>')
            model_name_input = ui.input(
                label='Model Name',
                placeholder='e.g., My-Awesome-LLM-7B'
            ).props('outlined dense clearable').classes('w-full md:w-1/2 enhanced-input')

            with ui.card_section():
                ui.label('Benchmark Scores').classes('text-md font-medium text-gray-700 mb-1')
                ui.html('<div class="helper-text" style="margin-bottom:0.5rem;">Scores are percentages. Recommended range: 0–100.</div>')
                with ui.element('div').classes('compare-grid'):
                    ifeval_input = ui.number(label='IFEval (%)', value=50.0, format='%.2f', step=0.01).props('outlined dense').classes('enhanced-number-input')
                    bbh_input = ui.number(label='BBH (%)', value=50.0, format='%.2f', step=0.01).props('outlined dense').classes('enhanced-number-input')
                    math_input = ui.number(label='MATH (%)', value=50.0, format='%.2f', step=0.01).props('outlined dense').classes('enhanced-number-input')
                    gpqa_input = ui.number(label='GPQA (%)', value=50.0, format='%.2f', step=0.01).props('outlined dense').classes('enhanced-number-input')
                    musr_input = ui.number(label='MUSR (%)', value=50.0, format='%.2f', step=0.01).props('outlined dense').classes('enhanced-number-input')
                    mmlu_pro_input = ui.number(label='MMLU-Pro (%)', value=50.0, format='%.2f', step=0.01).props('outlined dense').classes('enhanced-number-input')
            
            # Container for results and button
            custom_ranking_container = ui.element('div').classes('w-full mt-4')
            
            def clear_inputs():
                model_name_input.value = ''
                for el in [ifeval_input, bbh_input, math_input, gpqa_input, musr_input, mmlu_pro_input]:
                    el.value = None

            with ui.card_actions().classes('justify-end gap-2'):
                score_inputs = {
                    'IFEval': ifeval_input,
                    'BBH': bbh_input,
                    'MATH': math_input,
                    'GPQA': gpqa_input,
                    'MUSR': musr_input,
                    'MMLU-Pro': mmlu_pro_input
                }
                ui.button(
                    'Clear',
                    on_click=lambda: clear_inputs()
                ).props('flat').classes('enhanced-clear-btn')
                ui.button(
                    'Run Spectral Ranking',
                    on_click=lambda: handle_custom_ranking(model_name_input, score_inputs, custom_ranking_container, data)
                ).props('unelevated').classes('enhanced-run-btn')

    # Hugging Face Data Processing Steps
    with ui.element('section').style('width: 100%; max-width: 1400px; margin: 2rem auto; padding: 0 2rem;'):
        ui.html('<h2 class="section-title">How This Leaderboard is Calculated</h2>')
        
        with ui.element('div').classes('grid-container'):
            # Card 1: Data Collection & Preparation
            with ui.element('div').classes('step-card'):
                with ui.element('div').classes('card-header'):
                    with ui.element('div').classes('card-icon-container'):
                        ui.html('<span class="material-symbols-outlined card-icon">download_for_offline</span>')
                    ui.html('<h3 class="card-title">Step 1: Data Collection & Preparation</h3>')
                ui.html(r'''
                    <div class="card-description">
                        <ul>
                            <li><span class="material-symbols-outlined">dataset</span><div class="benchmark-item"><strong>Data Source:</strong> The process begins with the official <strong><a href="https://huggingface.co/datasets/open-llm-leaderboard/requests" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: bold;">Open LLM Leaderboard Dataset</a></strong> <span class="material-symbols-outlined" style="font-size: 0.875rem; color: #2563eb; vertical-align: middle;">open_in_new</span>, which contains performance data for thousands of models.</div></li>
                            <li><span class="material-symbols-outlined">filter_alt</span><div class="benchmark-item"><strong>Data Cleaning & Selection:</strong> We automatically download the latest data, then perform a rigorous cleaning process. This involves retaining the <strong>6 core benchmark scores</strong> (e.g., IFEval, MATH) and 9 key metadata columns, while filtering out any models with incomplete data. The top 100 models are then selected for analysis.</div></li>
                            <li><span class="material-symbols-outlined">transform</span><div class="benchmark-item"><strong>Data Transformation:</strong> The cleaned data, originally in a "model-per-row" format, is transformed into a <strong><code>6xN</code> "benchmark-vs-model" matrix</strong>. In this format, each row represents one of the 6 benchmarks, and each column represents a model. This matrix structure is the essential input required by the spectral ranking algorithm.</div></li>
                        </ul>
                    </div>
                ''')

            # Card 2: Spectral Ranking
            with ui.element('div').classes('step-card'):
                with ui.element('div').classes('card-header'):
                    with ui.element('div').classes('card-icon-container'):
                        ui.html('<span class="material-symbols-outlined card-icon">emoji_events</span>')
                    ui.html('<h3 class="card-title">Step 2: Spectral Ranking</h3>')
                ui.html(r'''
                    <div class="card-description">
                        <p>This final step aggregates the scores from the 6 key benchmarks into a single, highly robust global ranking using the <strong>Vanilla Spectral Method</strong>.</p>
                        <ul>
                            <li><span class="material-symbols-outlined">hub</span><div class="benchmark-item"><strong>Core Idea: A "Tournament Network"</strong>
                                 <p>The algorithm treats the 6 benchmarks as judges in a tournament. It then calculates a global <strong>"Power Score" (<code>theta.hat</code>)</strong> for each model by analyzing the entire network of comparisons. A model's score depends not just on its raw scores, but on how it performs relative to strong and weak competitors across all benchmarks, creating a more context-aware ranking.</p>
                             </div></li>
                            <li><span class="material-symbols-outlined">query_stats</span><div class="benchmark-item"><strong>Uncertainty & Confidence:</strong>
                                 <p>To test the stability of the ranking, the system runs thousands of simulations (via Weighted Bootstrap), slightly varying the data in each run. If a model consistently ranks high across these simulations, we have strong confidence in its position. This process generates the <strong>Confidence Intervals (CI)</strong> shown in the table.</p>
                             </div></li>
                             <li><span class="material-symbols-outlined">military_tech</span><div class="benchmark-item"><strong>Final Output:</strong> The result is the definitive "Spectral Rank" and its associated confidence intervals, providing a statistically sound and comprehensive final leaderboard that is more robust than a simple average.</div></li>
                        </ul>
                    </div>
                ''')

async def handle_custom_ranking(model_name_input, score_inputs, result_container, original_data):
    """Handle the custom model ranking request."""
    # Show enhanced loading animation
    with result_container:
        result_container.clear()
        with ui.element('div').classes('enhanced-loading-container'):
            with ui.element('div').classes('enhanced-loading-card'):
                # Animated icon container
                with ui.element('div').classes('enhanced-loading-icon-container'):
                    ui.html('<span class="material-symbols-outlined enhanced-loading-icon">analytics</span>')
                    # Animated dots
                    ui.html('<div class="enhanced-loading-dots"><span></span><span></span><span></span></div>')

                # Loading text with animation
                with ui.element('div').classes('enhanced-loading-text-container'):
                    ui.html('<div class="enhanced-loading-title">Running Spectral Ranking</div>')
                    ui.html('<div class="enhanced-loading-subtitle">Analyzing your model against the Top 100 leaderboard...</div>')
                    ui.html('<div class="enhanced-loading-note">This may take up to a minute</div>')

                # Progress indicator
                with ui.element('div').classes('enhanced-loading-progress'):
                    ui.html('<div class="enhanced-loading-bar"></div>')

    # Collect data
    model_name = model_name_input.value
    scores = {key: input_el.value for key, input_el in score_inputs.items()}

    # Basic validation
    if not model_name or any(s is None for s in scores.values()):
        with result_container:
            result_container.clear()
            ui.notify('Please fill in your model name and all benchmark scores.', type='negative')
        return

    custom_model_data = {
        "model_name": model_name,
        "scores": scores
    }

    try:
        # Call the backend API to run the ranking
        form = aiohttp.FormData()
        form.add_field('model_name', model_name)
        form.add_field('scores', json.dumps(scores))

        async with aiohttp.ClientSession() as session:
            async with session.post(f'{API_BASE_URL}/api/ranking/custom',
                                  data=form, timeout=120) as resp:
                if resp.status == 200:
                    new_ranking_data = await resp.json()
                else:
                    error_text = await resp.text()
                    raise Exception(f"API call failed: HTTP {resp.status} - {error_text}")

        with result_container:
            result_container.clear()

            # Find user's model data
            user_method = None
            total_models = len(new_ranking_data.get('methods', []))
            for method in new_ranking_data.get('methods', []):
                if method.get('name') == model_name:
                    user_method = method
                    break

            # Create comprehensive summary card (inspired by mode-card style)
            with ui.element('div').classes('custom-model-summary-card bg-white rounded-xl p-8 mb-6 shadow-lg border border-gray-200 transition-all duration-300 hover:shadow-xl'):
                # Header with icon and title (similar to mode-card)
                with ui.element('div').classes('flex items-center mb-6'):
                    with ui.element('div').classes('card-icon-container flex items-center justify-center w-16 h-16 rounded-full mr-4'):
                        ui.html('<span class="material-symbols-outlined card-icon">analytics</span>')
                    ui.html('<h3 class="text-2xl font-bold text-gray-800 m-0">Your Model Summary</h3>')

                if user_method:
                    rank = user_method.get('rank', 'N/A')
                    theta_hat = user_method.get('theta_hat', 'N/A')
                    ci_two_left = user_method.get('ci_two_sided', [None, None])[0]
                    ci_two_right = user_method.get('ci_two_sided', [None, None])[1]
                    ci_left = user_method.get('ci_left', 'N/A')
                    ci_uniform = user_method.get('ci_uniform_left', 'N/A')
                    scores_summary = user_method.get('benchmark_scores', {})

                    # Calculate score-based rank - rank by average score among all models
                    avg_score = scores_summary.get('average_score', 0)
                    score_rank = 'N/A'
                    if isinstance(avg_score, (int, float)) and total_models > 1:
                        # Get all models' average scores and sort to find user's rank
                        all_avg_scores = []
                        for method in new_ranking_data.get('methods', []):
                            method_avg = method.get('benchmark_scores', {}).get('average_score', 0)
                            if isinstance(method_avg, (int, float)):
                                all_avg_scores.append(method_avg)
                            else:
                                all_avg_scores.append(0)

                        # Sort in descending order (higher score = better rank)
                        sorted_scores = sorted(all_avg_scores, reverse=True)
                        try:
                            score_rank = sorted_scores.index(avg_score) + 1
                        except ValueError:
                            # If exact match fails, find approximate position
                            score_rank = sum(1 for s in sorted_scores if s > avg_score) + 1

                # Spectral Rank - centered and prominent
                with ui.element('div').classes('flex justify-center mb-8'):
                    with ui.element('div').classes('feature-item flex items-center p-6 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-all duration-200 shadow-sm max-w-lg w-full'):
                        ui.html('<span class="material-symbols-outlined text-4xl text-blue-600 mr-4">emoji_events</span>')
                        with ui.element('div').classes('flex-1 text-center'):
                            ui.html(f'<div class="text-4xl font-bold text-blue-700 mb-2">{rank}</div>')
                            ui.html('<div class="text-xl font-semibold text-gray-700 mb-1">Spectral Rank</div>')
                            ui.html('<div class="text-sm text-gray-500">Your ranking position among all models</div>')

                # Confidence Intervals section with θ-hat and CI metrics
                ui.html('<h4 class="text-xl font-semibold text-gray-800 mb-6">Confidence Intervals & Metrics</h4>')
                with ui.element('div').classes('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8'):
                    # θ-hat Score
                    with ui.element('div').classes('feature-item flex items-center p-5 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-all duration-200 shadow-sm'):
                        ui.html('<span class="material-symbols-outlined text-3xl text-blue-600 mr-4">analytics</span>')
                        with ui.element('div').classes('flex-1'):
                            theta_display = f"{theta_hat:.4f}" if isinstance(theta_hat, (int, float)) else theta_hat
                            ui.html(f'<div class="text-2xl font-bold text-blue-700">{theta_display}</div>')
                            ui.html('<div class="text-lg font-medium text-gray-700">θ-hat Score</div>')
                            ui.html('<div class="text-sm text-gray-500">Performance estimate from spectral ranking</div>')

                    # 95% Confidence Interval
                    with ui.element('div').classes('feature-item flex items-center p-5 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-all duration-200 shadow-sm'):
                        ui.html('<span class="material-symbols-outlined text-3xl text-purple-600 mr-4">query_stats</span>')
                        with ui.element('div').classes('flex-1'):
                            ci_display = f"[{ci_two_left}, {ci_two_right}]" if ci_two_left is not None and ci_two_right is not None else 'N/A'
                            ui.html(f'<div class="text-2xl font-bold text-purple-700">{ci_display}</div>')
                            ui.html('<div class="text-lg font-medium text-gray-700">95% CI</div>')
                            ui.html('<div class="text-sm text-gray-500">Two-sided confidence interval</div>')

                    # Left CI
                    with ui.element('div').classes('feature-item flex items-center p-5 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-all duration-200 shadow-sm'):
                        ui.html('<span class="material-symbols-outlined text-3xl text-indigo-600 mr-4">arrow_forward</span>')
                        with ui.element('div').classes('flex-1'):
                            ui.html(f'<div class="text-2xl font-bold text-indigo-700">≤{ci_left}</div>')
                            ui.html('<div class="text-lg font-medium text-gray-700">Left CI (95%)</div>')
                            ui.html('<div class="text-sm text-gray-500">One-sided confidence bound</div>')

                    # Uniform CI
                    with ui.element('div').classes('feature-item flex items-center p-5 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-all duration-200 shadow-sm'):
                        ui.html('<span class="material-symbols-outlined text-3xl text-teal-600 mr-4">verified</span>')
                        with ui.element('div').classes('flex-1'):
                            ui.html(f'<div class="text-2xl font-bold text-teal-700">≤{ci_uniform}</div>')
                            ui.html('<div class="text-lg font-medium text-gray-700">Uniform CI</div>')
                            ui.html('<div class="text-sm text-gray-500">Simultaneous bound for all models</div>')

                # Benchmark performance in feature style
                ui.html('<h4 class="text-xl font-semibold text-gray-800 mb-4">Benchmark Performance</h4>')
                with ui.element('div').classes('grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6'):
                    benchmarks = [
                        ('IFEval', 'ifeval', '#3b82f6', 'Instruction following evaluation'),
                        ('BBH', 'bbh', '#ef4444', 'Big-bench hard tasks'),
                        ('MATH', 'math', '#f59e0b', 'Mathematical reasoning'),
                        ('GPQA', 'gpqa', '#8b5cf6', 'Graduate-level Q&A'),
                        ('MUSR', 'musr', '#10b981', 'Multi-step reasoning'),
                        ('MMLU-Pro', 'mmlu_pro', '#f97316', 'Advanced knowledge'),
                        ('Average', 'average_score', '#6366f1', 'Overall performance')
                    ]

                    for bench_name, bench_key, color, description in benchmarks:
                        score = scores_summary.get(bench_key, 'N/A')
                        score_display = f"{score:.2f}%" if isinstance(score, (int, float)) else score
                        with ui.element('div').classes('benchmark-feature p-4 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-all duration-200 hover:border-gray-300'):
                            with ui.element('div').classes('flex items-center justify-between mb-2'):
                                ui.html(f'<span class="text-sm font-semibold text-gray-700">{bench_name}</span>')
                                ui.html(f'<span class="text-lg font-bold" style="color: {color}">{score_display}</span>')
                            ui.html(f'<div class="text-xs text-gray-500">{description}</div>')

                    # Add Score Rank next to Average
                    with ui.element('div').classes('benchmark-feature p-4 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-all duration-200 hover:border-gray-300'):
                        with ui.element('div').classes('flex items-center justify-between mb-2'):
                            ui.html('<span class="text-sm font-semibold text-gray-700">Score Rank</span>')
                            ui.html(f'<span class="text-lg font-bold text-gray-600">{score_rank}</span>')
                        ui.html('<div class="text-xs text-gray-500">Average-based ranking position</div>')

            ui.html(f'<h3 class="section-title text-xl font-semibold mb-4">Full Ranking Results (101 models)</h3>')
            
            # Display the new table, highlighting the user's model
            create_ranking_table({'spectral_results': new_ranking_data}, highlight_model=model_name)

    except Exception as e:
        logger.error(f"Custom ranking error: {e}")
        with result_container:
            result_container.clear()
            ui.notify(f'An error occurred during ranking: {e}', type='negative')

def create_arena_content(data):
    """Create content for Arena mode"""
    # Metrics Overview
    with ui.element('section').style('width: 100%; max-width: 1400px; margin: 0 auto; padding: 0 2rem;'):
        ui.html('<h2 class="section-title">LMSYS Arena Overview</h2>')
        create_metrics_overview(data, is_arena_mode=True)

    # Rankings Table
    with ui.element('section').style('width: 100%; max-width: 1400px; margin: 0 auto; padding: 0 2rem;'):
        # Determine the number of models being displayed
        spectral_results = data.get('spectral_results')
        if spectral_results and 'methods' in spectral_results:
            display_count = len(spectral_results['methods'])
        else:
            display_count = min(20, len(data.get('models', [])))

        ui.html(f'<h2 class="section-title">Top {display_count} LMSYS Arena LLM Rankings</h2>')
        create_ranking_table(data)

    # Arena-specific information - Data Processing Steps
    with ui.element('section').style('width: 100%; max-width: 1400px; margin: 2rem auto; padding: 0 2rem;'):
        ui.html('<h2 class="section-title">How This Leaderboard is Calculated</h2>')
        
        with ui.element('div').classes('grid-container'):
            # Card 1: Data Source
            with ui.element('div').classes('step-card'):
                with ui.element('div').classes('card-header'):
                    with ui.element('div').classes('card-icon-container'):
                        ui.html('<span class="material-symbols-outlined card-icon">database</span>')
                    ui.html('<h3 class="card-title">Step 1: Data Source</h3>')
                ui.html('''
                    <div class="card-description">
                        <ul>
                            <li><span class="material-symbols-outlined">database</span><div class="benchmark-item"><strong>Dataset:</strong> <a href="https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k" target="_blank" style="color: #2563eb; text-decoration: underline; font-weight: bold;"><code>lmarena-ai/arena-human-preference-140k</code></a> <span class="material-symbols-outlined" style="font-size: 0.875rem; color: #2563eb; vertical-align: middle;">open_in_new</span></div></li>
                            <li><span class="material-symbols-outlined">storage</span><div class="benchmark-item"><strong>Data Scale:</strong> Contains 135,634 battle records featuring 53 unique models, totaling 1.61 GB of data.</div></li>
                            <li><span class="material-symbols-outlined">groups</span><div class="benchmark-item"><strong>Collection:</strong> Crowdsourced from anonymous users on the <a href="https://lmarena.ai/leaderboard" target="_blank" style="color: #2563eb; text-decoration: underline;">Chatbot Arena</a> platform, reflecting real-world interactions.</div></li>
                            <li><span class="material-symbols-outlined">compare_arrows</span><div class="benchmark-item"><strong>Mechanism:</strong> Users blindly chat with two models (<code>model_a</code>, <code>model_b</code>) and vote for their preferred response. Vote outcomes can be a win for either model, a <code>tie</code>, or a judgment that <code>both are bad</code>.</div></li>
                            <li><span class="material-symbols-outlined">fact_check</span><div class="benchmark-item"><strong>Rich Content:</strong> Each record includes the full conversation history, the final vote (<code>winner</code>), and structured annotation tags (<code>category_tag</code>) for deep analysis.</div></li>
                            <li><span class="material-symbols-outlined">copyright</span><div class="benchmark-item"><strong>License:</strong> User prompts are licensed under CC-BY-4.0, ensuring data openness and reusability.</div></li>
                        </ul>
                </div>
                ''')

            # Card 2: Categorization
            with ui.element('div').classes('step-card'):
                with ui.element('div').classes('card-header'):
                    with ui.element('div').classes('card-icon-container'):
                        ui.html('<span class="material-symbols-outlined card-icon">fact_check</span>')
                    ui.html('<h3 class="card-title">Step 2: Virtual Benchmarks</h3>')
                ui.html('''
                    <div class="card-description">
                        <p>To enable a granular analysis, each battle is categorized into <strong>7 virtual benchmarks</strong> based on its content, metadata, and official Arena definitions:</p>
                        <ul>
                            <li><span class="material-symbols-outlined">palette</span><div class="benchmark-item"><strong>Creative Writing:</strong> Evaluates originality and imagination. Identified by the <code>creative_writing</code> tag.</div></li>
                            <li><span class="material-symbols-outlined">calculate</span><div class="benchmark-item"><strong>Math:</strong> Assesses mathematical reasoning. Identified by the <code>math</code> tag.</div></li>
                            <li><span class="material-symbols-outlined">rule</span><div class="benchmark-item"><strong>Instruction Following:</strong> Measures precision in following user commands. Identified by the <code>if</code> tag.</div></li>
                            <li><span class="material-symbols-outlined">code</span><div class="benchmark-item"><strong>Coding:</strong> Judges the ability to generate and debug code. Identified when <code>is_code == True</code>.</div></li>
                            <li><span class="material-symbols-outlined">psychology</span><div class="benchmark-item"><strong>Hard Prompt:</strong> Tests performance on prompts meeting at least 6 of 7 complexity criteria (e.g., specificity, domain knowledge, problem-solving). <a href="https://lmsys.org/blog/2024-05-17-category-hard/" target="_blank" style="color: #2563eb; text-decoration: underline;">Introducing Hard Prompts Category in Chatbot Arena</a></div></li>
                            <li><span class="material-symbols-outlined">subject</span><div class="benchmark-item"><strong>Longer Query:</strong> Focuses on prompts where user input exceeds 500 tokens.</div></li>
                            <li><span class="material-symbols-outlined">forum</span><div class="benchmark-item"><strong>Multi-Turn:</strong> Evaluates performance in conversations that involve more than one turn.</div></li>
                        </ul>
                        <div class="card-footer">
                            <strong>Source:</strong> For detailed criteria, see <a href="https://news.lmarena.ai/arena-category/" target="_blank" style="color: #2563eb; text-decoration: underline;">Chatbot Arena Categories</a>.
                        </div>
                    </div>
                ''')

            # Card 3: BT-MLE Modeling
            with ui.element('div').classes('step-card'):
                with ui.element('div').classes('card-header'):
                    with ui.element('div').classes('card-icon-container'):
                        ui.html('<span class="material-symbols-outlined card-icon">calculate</span>')
                    ui.html('<h3 class="card-title">Step 3: BT-MLE Modeling</h3>')
                ui.html(r'''
                    <div class="card-description">
                        <p>To ensure statistical robustness, we use the <strong>Bradley-Terry (BT) model</strong>, which is the Maximum Likelihood Estimation (MLE) of the underlying Elo model. This approach is fundamentally more robust than a simple win rate.</p>
                        <ul>
                            <li><span class="material-symbols-outlined">balance</span><div class="benchmark-item"><strong>Why Not a Simple Win Rate?</strong>
                                <div class="advantage-list">
                                    <div class="advantage-item">
                                        <span class="material-symbols-outlined">military_tech</span>
                                        <div>
                                            <strong>It ignores opponent strength.</strong>
                                            <p>A simple win rate (Wins / Total Games) is misleading. A win against a top-tier model should count for more than a win against a weaker one. The BT model solves this by estimating a latent "ability score" for each model.</p>
                                        </div>
                                    </div>
                                </div>
                            </div></li>
                            <li><span class="material-symbols-outlined">upgrade</span><div class="benchmark-item"><strong>Why BT-MLE over Online Elo?</strong>
                                <div class="advantage-list">
                                    <div class="advantage-item">
                                        <span class="material-symbols-outlined">show_chart</span>
                                        <div>
                                            <strong>Traditional Elo is for dynamic players.</strong>
                                            <p>It assumes performance changes over time (like chess players). For static LLMs, this can lead to rating instability.</p>
                                        </div>
                                    </div>
                                    <div class="advantage-item">
                                        <span class="material-symbols-outlined">verified</span>
                                        <div>
                                            <strong>BT-MLE is for static models.</strong>
                                            <p>It analyzes all game data at once, resulting in significantly more stable ratings and precise confidence intervals.</p>
                                        </div>
                                    </div>
                                </div>
                            </div></li>
                             <li><span class="material-symbols-outlined">functions</span><div class="benchmark-item"><strong>Core Formula:</strong> The probability of model \(i\) winning against model \(j\) is given by:<br><div style="text-align: center; margin: 0.5rem 0; font-size: 1.1em;">\[\Pr(i > j) = \sigma(\theta_i - \theta_j) = \frac{\exp(\theta_i)}{\exp(\theta_i)+\exp(\theta_j)}\]</div>Here, \(\theta_i\) represents the latent ability score of model \(i\), and the scores for all models are estimated simultaneously to best explain the entire history of outcomes.</div></li>
                            <li><span class="material-symbols-outlined">analytics</span><div class="benchmark-item"><strong>Output (BT Probability):</strong> The result is a robust "BT probability" for each model in each of the 7 categories, forming the basis for the final spectral ranking.</div></li>
                        </ul>
                        <div class="card-footer">
                            <strong>Reference:</strong> This methodology aligns with the official <a href="https://lmsys.org/blog/2023-12-07-leaderboard/" target="_blank" style="color: #2563eb; text-decoration: underline;">Chatbot Arena Elo system update</a>.
                        </div>
                    </div>
                ''')

            # Card 4: Spectral Ranking
            with ui.element('div').classes('step-card'):
                with ui.element('div').classes('card-header'):
                    with ui.element('div').classes('card-icon-container'):
                        ui.html('<span class="material-symbols-outlined card-icon">emoji_events</span>')
                    ui.html('<h3 class="card-title">Step 4: Spectral Ranking</h3>')
                ui.html(r'''
                    <div class="card-description">
                        <p>This final, crucial step aggregates the nuanced scores from the 7 virtual benchmarks into a single, highly robust global ranking using the <strong>Vanilla Spectral Method</strong>.</p>
                        <ul>
                            <li><span class="material-symbols-outlined">hub</span><div class="benchmark-item"><strong>Core Idea: A "Tournament Network"</strong>
                                 <p>The algorithm treats all comparisons as a large tournament network. It then calculates a global <strong>"Power Score"</strong> (<code>theta.hat</code>) for each model. A model's score depends not just on winning, but on the strength of the opponents it beats, creating a much more context-aware and fair ranking than a simple average.</p>
                             </div></li>
                            <li><span class="material-symbols-outlined">query_stats</span><div class="benchmark-item"><strong>Uncertainty & Confidence:</strong>
                                 <p>To test the stability of the ranking, the system runs thousands of simulations (Weighted Bootstrap), slightly varying the data each time. If a model consistently ranks high, we have strong confidence in its position. This process generates the <strong>Confidence Intervals (CI)</strong>, telling you how reliable the final rank is.</p>
                             </div></li>
                            <li><span class="material-symbols-outlined">emoji_events</span><div class="benchmark-item"><strong>Final Output:</strong> The result is the definitive "Spectral Rank" and its associated confidence intervals, providing a statistically sound and comprehensive final leaderboard.</div></li>
                        </ul>
                    </div>
            ''')

def create_dashboard():
    """Main function to create the LLM Performance Dashboard"""
    # Main UI Layout with dashboard-specific class to avoid style conflicts
    with ui.element('div').classes('dashboard-container').style('min-height: 100vh; width: 100vw; display: flex; flex-direction: column; align-items: center; padding: 0; margin: 0;'):

        # Add MathJax for LaTeX rendering
        ui.add_head_html('<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>')

        # Add JavaScript for table sorting
        ui.add_head_html('''
            <script>
                function sortTable(headerElement, columnIndex, tableId) {
                    const table = document.getElementById(tableId);
                    if (!table) return;
                    const tbody = table.querySelector('tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    
                    const currentIsAsc = headerElement.classList.contains('sorted-asc');
                    let newSortDir;

                    // Reset all other headers' sorting classes
                    table.querySelectorAll('th.sortable-header').forEach(th => {
                        if (th !== headerElement) {
                            th.classList.remove('sorted-asc', 'sorted-desc');
                        }
                    });

                    // Determine new sort direction
                    if (currentIsAsc) {
                        newSortDir = 'desc';
                        headerElement.classList.remove('sorted-asc');
                        headerElement.classList.add('sorted-desc');
                    } else {
                        newSortDir = 'asc';
                        headerElement.classList.remove('sorted-desc');
                        headerElement.classList.add('sorted-asc');
                    }

                    const direction = newSortDir === 'asc' ? 1 : -1;

                    // Sort the rows
                    rows.sort((a, b) => {
                        const cellA = a.cells[columnIndex];
                        const cellB = b.cells[columnIndex];
                        
                        if (!cellA || !cellB) return 0;

                        let valA = cellA.textContent.trim();
                        let valB = cellB.textContent.trim();
                        
                        // Check if the first non-N/A value is numeric
                        const isNumeric = rows.map(r => r.cells[columnIndex].textContent.trim()).find(v => v !== 'N/A' && !isNaN(parseFloat(v.replace(/[^0-9.-]/g, ''))));

                        if (isNumeric !== undefined) {
                            const numA = valA === 'N/A' ? -Infinity * direction : parseFloat(valA.replace(/[^0-9.-]/g, ''));
                            const numB = valB === 'N/A' ? -Infinity * direction : parseFloat(valB.replace(/[^0-9.-]/g, ''));
                            return (numA - numB) * direction;
                        } else {
                            return valA.localeCompare(valB) * direction;
                        }
                    });

                    // Re-append sorted rows
                    tbody.innerHTML = '';
                    rows.forEach(row => tbody.appendChild(row));
                }
            </script>
        ''')

        # Top Navigation Bar - same as main page
        with ui.element('nav').classes('top-navbar'):
            # Brand/Logo section
            with ui.element('div').classes('navbar-brand'):
                ui.html('<span class="navbar-brand-icon">Σ</span>')
                ui.html('<a href="#" onclick="window.location.href=\'/\'" class="navbar-brand-link">Spectral Ranking</a>')

            # Main navigation menu (hidden on mobile)
            with ui.element('ul').classes('navbar-nav'):
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="/dashboard" class="nav-link active">Dashboard</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#mode-selection" onclick="window.location.href=\'/#mode-selection\'" class="nav-link">Analysis</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#results" onclick="window.location.href=\'/#results\'" class="nav-link">Results</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#documentation" onclick="window.location.href=\'/#documentation\'" class="nav-link">Help</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#about" onclick="window.location.href=\'/#about\'" class="nav-link">About</a>')

            # Right side actions
            with ui.element('div').classes('navbar-actions'):
                ui.html('<a href="https://github.com/MaxineYu/Spectral_Ranking" class="nav-button primary" target="_blank"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/github/github-original.svg" alt="GitHub" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle; filter: brightness(0) invert(1);"/>GitHub</a>')
                ui.html('<a href="https://doi.org/10.1287/opre.2023.0439" class="nav-button primary" target="_blank"><img src="https://arxiv.org/static/browse/0.3.4/images/arxiv-logo-one-color-white.svg" alt="arXiv" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle; filter: brightness(0) invert(1);"/>Read the Paper</a>')

            # Mobile menu toggle (visible only on mobile)
            with ui.element('button').classes('mobile-toggle').on('click', toggle_mobile_nav):
                ui.html('☰')

            # Mobile navigation menu (hidden by default)
            with ui.element('div').classes('mobile-nav'):
                with ui.element('ul').classes('navbar-nav'):
                    with ui.element('li').classes('nav-item'):
                        ui.html('<a href="/dashboard" class="nav-link active">Dashboard</a>')
                    with ui.element('li').classes('nav-item'):
                        ui.html('<a href="#mode-selection" onclick="window.location.href=\'/#mode-selection\'" class="nav-link">Analysis</a>')
                    with ui.element('li').classes('nav-item'):
                        ui.html('<a href="#results" onclick="window.location.href=\'/#results\'" class="nav-link">Results</a>')
                    with ui.element('li').classes('nav-item'):
                        ui.html('<a href="#documentation" onclick="window.location.href=\'/#documentation\'" class="nav-link">Help</a>')
                    with ui.element('li').classes('nav-item'):
                        ui.html('<a href="#about" onclick="window.location.href=\'/#about\'" class="nav-link">About</a>')

                with ui.element('div').classes('navbar-actions'):
                    ui.html('<a href="https://github.com/MaxineYu/Spectral_Ranking" class="nav-button primary" target="_blank"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/github/github-original.svg" alt="GitHub" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle; filter: brightness(0) invert(1);"/>GitHub</a>')
                    ui.html('<a href="https://doi.org/10.1287/opre.2023.0439" class="nav-button primary" target="_blank"><img src="https://arxiv.org/static/browse/0.3.4/images/arxiv-logo-one-color-white.svg" alt="arXiv" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle; filter: brightness(0) invert(1);"/>Read the Paper</a>')

        # Main Content
        create_dashboard_content()

# Run the dashboard
if __name__ in {"__main__", "__mp_main__"}:
    create_dashboard()
    ui.run(port=8002, title="LLM Performance Dashboard")
