from nicegui import ui
import requests
import json
import plotly.graph_objects as go
import asyncio
import aiohttp
import logging
import sys
import os

# Add the current directory to the path to import dashboard
sys.path.append(os.path.dirname(__file__))
from dashboard import create_dashboard

# API configuration - use environment variable for production
API_BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:8001')
API_BASE = f'{API_BASE_URL}/api/ranking'

# Dashboard route
@ui.page('/dashboard')
def dashboard_page():
    """Dashboard page for LLM performance visualization"""
    # Add dashboard-specific CSS for this page
    ui.add_head_html('''
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
<style>
:root {
  /* Primary theme colors based on #011f5b */
  --primary-50: #eff8ff;
  --primary-100: #dbeafe;
  --primary-200: #bfdbfe;
  --primary-300: #93c5fd;
  --primary-400: #60a5fa;
  --primary-500: #3b82f6;
  --primary-600: #2563eb;
  --primary-700: #1d4ed8;
  --primary-800: #1e40af;
  --primary-900: #011f5b;
  --primary-950: #001127;

  /* Extended color palette */
  --accent-400: #34d399;
  --accent-500: #10b981;
  --accent-600: #059669;
  --warning-400: #fbbf24;
  --warning-500: #f59e0b;
  --warning-600: #d97706;
  --error-400: #f87171;
  --error-500: #ef4444;
  --error-600: #dc2626;

  /* Neutral colors */
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-400: #9ca3af;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --gray-700: #374151;
  --gray-800: #1f2937;
  --gray-900: #111827;

  /* Semantic colors */
  --success: var(--accent-500);
  --warning: var(--warning-500);
  --error: var(--error-500);
  --info: var(--primary-600);

  /* Background gradients */
  --bg-gradient-primary: linear-gradient(135deg, #011f5b 25%, #1e40af 75%, #1d4ed8 100%);
  --bg-gradient-light: linear-gradient(135deg, var(--gray-50) 0%, var(--primary-50) 100%);
  --bg-gradient-card: linear-gradient(145deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%);

  /* Shadows */
  --shadow-xs: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
  --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
  --shadow-colored: 0 20px 25px -5px rgba(1, 31, 91, 0.1), 0 8px 10px -6px rgba(1, 31, 91, 0.1);

  /* Border radius */
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --radius-2xl: 1.5rem;
  --radius-3xl: 2rem;

  /* Animations */
  --transition-fast: all 0.15s ease;
  --transition-base: all 0.2s ease;
  --transition-slow: all 0.3s ease;
  --transition-bounce: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg-gradient-light);
  color: var(--gray-900);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Dashboard-specific styles to avoid conflicts with main app */
.dashboard-container .top-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2000;
  background: rgba(1, 31, 91, 0.95);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0 1.5rem;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.dashboard-container .top-navbar.scrolled {
  background: rgba(1, 31, 91, 0.98);
  box-shadow: var(--shadow-lg);
}

.dashboard-container .navbar-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 700;
  font-size: 1.25rem;
}

.dashboard-container .navbar-brand-link {
  color: white !important;
  text-decoration: none;
  transition: var(--transition-base);
}

.dashboard-container .navbar-brand-link:hover {
  color: var(--primary-200) !important;
  transform: translateY(-1px);
}

.dashboard-container .navbar-brand-icon {
  font-size: 1.5rem;
  color: white;
}

.dashboard-container .navbar-nav {
  display: flex;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 2rem;
}

.dashboard-container .nav-item {
  position: relative;
}

.dashboard-container .nav-link {
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  transition: var(--transition-base);
  position: relative;
}

.dashboard-container .nav-link:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.dashboard-container .nav-link::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 50%;
  width: 0;
  height: 2px;
  background: white;
  transition: var(--transition-base);
  transform: translateX(-50%);
}

.dashboard-container .nav-link:hover::after {
  width: 100%;
}

.dashboard-container .nav-link.active {
  color: white;
  background: rgba(255, 255, 255, 0.15);
}

.dashboard-container .nav-link.active::after {
  width: 100%;
  background: white;
}

.dashboard-container .navbar-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.dashboard-container .nav-button {
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  font-weight: 500;
  font-size: 0.875rem;
  text-decoration: none;
  transition: var(--transition-base);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.dashboard-container .nav-button.primary {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.dashboard-container .nav-button.primary:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.dashboard-container .mobile-toggle {
  display: none;
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: var(--radius-md);
  transition: var(--transition-base);
}

.dashboard-container .mobile-toggle:hover {
  background: rgba(255, 255, 255, 0.1);
}

.dashboard-container .mobile-nav {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: rgba(1, 31, 91, 0.98);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding: 1rem 2rem;
}

/* Hero Section */
.dashboard-container .hero-section {
  padding: 120px 2rem 4rem;
  text-align: center;
  background: var(--bg-gradient-light);
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dashboard-container .hero-content {
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-container .hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--primary-900);
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-colored);
}

.dashboard-container .hero-title {
  font-size: clamp(2.5rem, 5vw, 4rem);
  font-weight: 900;
  color: var(--primary-900);
  margin-bottom: 1.5rem;
  letter-spacing: -0.02em;
  line-height: 1.1;
}

.dashboard-container .hero-subtitle {
  font-size: clamp(1.1rem, 2.5vw, 1.375rem);
  color: var(--gray-600);
  margin-bottom: 3rem;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.6;
}

.dashboard-container .hero-features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-top: 3rem;
}

.dashboard-container .hero-feature {
  background: var(--bg-gradient-card);
  padding: 2rem;
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-md);
  border: 1px solid rgba(255, 255, 255, 0.5);
  transition: var(--transition-base);
}

.dashboard-container .hero-feature:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-xl);
}

.dashboard-container .hero-feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  display: block;
}

.dashboard-container .hero-feature-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--primary-900);
  margin-bottom: 1rem;
}

.dashboard-container .hero-feature-description {
  color: var(--gray-600);
  font-size: 0.95rem;
  line-height: 1.6;
}

/* Info Cards */
.dashboard-container .info-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-xl);
  padding: 2rem;
  margin: 1.5rem 0;
  box-shadow: var(--shadow-sm);
  transition: var(--transition-slow);
  position: relative;
  overflow: hidden;
}

.dashboard-container .info-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--bg-gradient-primary);
  transition: var(--transition-base);
  transform: scaleY(0);
  transform-origin: top;
}

.dashboard-container .info-card:hover::before {
  transform: scaleY(1);
}

.dashboard-container .info-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

/* Plot Containers */
.dashboard-container .plot-container {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-xl);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);
  overflow: hidden;
}

.dashboard-container .plot-container:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* Modern Tables */
.dashboard-container .modern-table .q-table__container {
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.dashboard-container .modern-table .q-table thead th {
  background: var(--primary-900);
  color: white;
  font-weight: 600;
  padding: 1rem;
  border: none;
}

.dashboard-container .modern-table .q-table tbody td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--gray-200);
}

.dashboard-container .modern-table .q-table tbody tr:hover {
  background: var(--primary-50);
}

/* Badges */
.dashboard-container .badge {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);
}

.dashboard-container .badge:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
}

.dashboard-container .badge.primary {
  background: var(--primary-900);
  color: white;
}

.dashboard-container .badge.success {
  background: var(--accent-500);
  color: white;
}

.dashboard-container .badge.warning {
  background: var(--warning-500);
  color: white;
}

.dashboard-container .badge.error {
  background: var(--error-500);
  color: white;
}

/* Section Titles */
.dashboard-container .section-title {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--primary-900);
  margin-bottom: 2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  position: relative;
}

.dashboard-container .section-title::before {
  content: '';
  width: 6px;
  height: 2rem;
  background: var(--bg-gradient-primary);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
}

/* Responsive Design */
@media (max-width: 768px) {
  .dashboard-container .top-navbar {
    padding: 0 1rem;
  }

  .dashboard-container .navbar-nav {
    display: none;
  }

  .dashboard-container .mobile-toggle {
    display: block;
  }

  .dashboard-container .hero-section {
    padding: 100px 1rem 2rem;
  }

  .dashboard-container .hero-title {
    font-size: clamp(2rem, 8vw, 3rem);
  }

  .dashboard-container .hero-features {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .dashboard-container .info-card {
    padding: 1.25rem;
    margin: 1rem 0;
  }

  .dashboard-container .section-title {
    font-size: 1.5rem;
  }

  .dashboard-container .plot-container {
    padding: 1rem;
  }
}

/* Scrollbar styling */
.dashboard-container ::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.dashboard-container ::-webkit-scrollbar-track {
  background: var(--gray-100);
  border-radius: var(--radius-sm);
}

.dashboard-container ::-webkit-scrollbar-thumb {
  background: var(--primary-900);
  border-radius: var(--radius-sm);
}

.dashboard-container ::-webkit-scrollbar-thumb:hover {
  background: var(--primary-950);
}

/* Loading Spinner */
.dashboard-container .loading-spinner {
  display: inline-block;
  width: 2rem;
  height: 2rem;
  border: 3px solid var(--primary-200);
  border-radius: 50%;
  border-top-color: var(--primary-900);
  animation: spin 1s linear infinite;
  box-shadow: var(--shadow-sm);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Ranking Table Styles */
.dashboard-container .ranking-table {
  background: rgba(255, 255, 255, 0.9);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
  margin: 2rem 0;
}

.dashboard-container .ranking-header {
  background: var(--bg-gradient-primary);
  color: white;
  padding: 1.5rem 2rem;
  font-size: 1.25rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.dashboard-container .ranking-header-icon {
  font-size: 1.5rem;
}

.dashboard-container .ranking-content {
  padding: 0;
}

/* Metric Cards */
.dashboard-container .metric-card {
  background: var(--bg-gradient-card);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  text-align: center;
  box-shadow: var(--shadow-md);
  transition: var(--transition-base);
}

.dashboard-container .metric-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

.dashboard-container .metric-value {
  font-size: 2rem;
  font-weight: 900;
  color: var(--primary-900);
  margin-bottom: 0.5rem;
}

.dashboard-container .metric-label {
  font-size: 0.875rem;
  color: var(--gray-600);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Model Cards */
.dashboard-container .model-card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin: 0.5rem 0;
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);
}

.dashboard-container .model-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-300);
}

.dashboard-container .model-rank {
  font-size: 1.5rem;
  font-weight: 900;
  color: var(--primary-900);
  margin-bottom: 0.5rem;
}

.dashboard-container .model-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--gray-900);
  margin-bottom: 0.25rem;
}

.dashboard-container .model-score {
  font-size: 0.9rem;
  color: var(--gray-600);
  margin-bottom: 0.5rem;
}

.dashboard-container .model-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: 0.5rem;
  font-size: 0.8rem;
}

.dashboard-container .metric-item {
  background: var(--gray-50);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  text-align: center;
}

.dashboard-container .metric-name {
  font-weight: 600;
  color: var(--gray-700);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dashboard-container .metric-score {
  color: var(--primary-900);
  font-weight: 700;
}

/* Chart Styles */
.dashboard-container .chart-container {
  background: rgba(255, 255, 255, 0.9);
  border-radius: var(--radius-xl);
  padding: 2rem;
  box-shadow: var(--shadow-lg);
  margin: 2rem 0;
}

.dashboard-container .chart-title {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--primary-900);
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.dashboard-container .chart-title-icon {
  font-size: 1.25rem;
  color: var(--accent-500);
}
</style>
''')
    create_dashboard()

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE = f'{API_BASE_URL}/api/ranking' 

# Global references for shared UI containers and elements
report_container_ref = None
status_container_ref = None
suggestions_area_ref = None
mobile_nav_ref = None
agent_data_preview_ref = None

# Enhanced CSS styling with #011f5b theme
ui.add_head_html('''
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
<style>
:root {
  /* Primary theme colors based on #011f5b */
  --primary-50: #eff8ff;
  --primary-100: #dbeafe;
  --primary-200: #bfdbfe;
  --primary-300: #93c5fd;
  --primary-400: #60a5fa;
  --primary-500: #3b82f6;
  --primary-600: #2563eb;
  --primary-700: #1d4ed8;
  --primary-800: #1e40af;
  --primary-900: #011f5b;
  --primary-950: #001127;
  
  /* Extended color palette */
  --accent-400: #34d399;
  --accent-500: #10b981;
  --accent-600: #059669;
  --warning-400: #fbbf24;
  --warning-500: #f59e0b;
  --warning-600: #d97706;
  --error-400: #f87171;
  --error-500: #ef4444;
  --error-600: #dc2626;
  
  /* Neutral colors */
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-400: #9ca3af;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --gray-700: #374151;
  --gray-800: #1f2937;
  --gray-900: #111827;
  
  /* Semantic colors */
  --success: var(--accent-500);
  --warning: var(--warning-500);
  --error: var(--error-500);
  --info: var(--primary-600);
  
  /* Background gradients */
  --bg-gradient-primary: linear-gradient(135deg, #011f5b 25%, #1e40af 75%, #1d4ed8 100%);
  --bg-gradient-light: linear-gradient(135deg, var(--gray-50) 0%, var(--primary-50) 100%);
  --bg-gradient-card: linear-gradient(145deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%);
  
  /* Shadows */
  --shadow-xs: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
  --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
  --shadow-colored: 0 20px 25px -5px rgba(1, 31, 91, 0.1), 0 8px 10px -6px rgba(1, 31, 91, 0.1);
  
  /* Border radius */
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --radius-2xl: 1.5rem;
  --radius-3xl: 2rem;
  
  /* Animations */
  --transition-fast: all 0.15s ease;
  --transition-base: all 0.2s ease;
  --transition-slow: all 0.3s ease;
  --transition-bounce: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

* {
  box-sizing: border-box;
}

body, html {
  margin: 0;
  padding: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  background: var(--bg-gradient-light);
  min-height: 100vh;
  scroll-behavior: smooth;
  overflow-x: hidden; /* Prevent horizontal scroll */
}

/* Global animations */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInScale {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .8; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes float {
  0% {
    transform: translateY(0) scale(1);
    opacity: 0;
  }
  50% {
    opacity: 0.8;
  }
  100% {
    transform: translateY(-100vh) scale(0.8);
    opacity: 0;
  }
}

/* Enhanced Hero Section */
.hero-section {
  background: linear-gradient(135deg, #1e3a8a 0%, #011f5b 40%, #000d26 80%, #00071a 100%);
  color: white;
  padding: 0;
  margin: 0;
  border-radius: 0;
  box-shadow: none;
  position: relative;
  overflow: hidden;
  animation: fadeInScale 0.8s ease-out;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    radial-gradient(circle at 20% 30%, rgba(1, 31, 91, 0.3) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(0, 17, 51, 0.4) 0%, transparent 50%),
    radial-gradient(circle at 50% 50%, rgba(0, 10, 26, 0.2) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
}

.hero-section::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.02) 50%, transparent 60%);
  animation: waterShimmer 8s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes waterShimmer {
  0%, 100% {
    opacity: 0.3;
    transform: translateX(-10px) translateY(-5px);
  }
  50% {
    opacity: 0.8;
    transform: translateX(10px) translateY(5px);
  }
}

.hero-floating-particles {
  display: block !important;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  z-index: 1;
}

.hero-floating-particles .particle {
  position: absolute;
  bottom: -100px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  animation: float 25s infinite linear;
  opacity: 0;
}

.hero-floating-particles .particle:nth-child(1) { width: 4px; height: 4px; left: 10%; animation-duration: 20s; animation-delay: 0s; }
.hero-floating-particles .particle:nth-child(2) { width: 2px; height: 2px; left: 25%; animation-duration: 30s; animation-delay: -5s; }
.hero-floating-particles .particle:nth-child(3) { width: 5px; height: 5px; left: 40%; animation-duration: 15s; animation-delay: -10s; }
.hero-floating-particles .particle:nth-child(4) { width: 3px; height: 3px; left: 55%; animation-duration: 22s; animation-delay: -1s; }
.hero-floating-particles .particle:nth-child(5) { width: 2px; height: 2px; left: 70%; animation-duration: 28s; animation-delay: -15s; }
.hero-floating-particles .particle:nth-child(6) { width: 4px; height: 4px; left: 85%; animation-duration: 18s; animation-delay: -8s; }
.hero-floating-particles .particle:nth-child(7) { width: 3px; height: 3px; left: 5%; animation-duration: 26s; animation-delay: -4s; }
.hero-floating-particles .particle:nth-child(8) { width: 2px; height: 2px; left: 95%; animation-duration: 32s; animation-delay: -18s; }
.hero-floating-particles .particle:nth-child(9) { width: 5px; height: 5px; left: 50%; animation-duration: 14s; animation-delay: -20s; }
.hero-floating-particles .particle:nth-child(10) { width: 3px; height: 3px; left: 15%; animation-duration: 24s; animation-delay: -2s; }
.hero-floating-particles .particle:nth-child(11) { width: 4px; height: 4px; left: 30%; animation-duration: 19s; animation-delay: -7s; }
.hero-floating-particles .particle:nth-child(12) { width: 2px; height: 2px; left: 45%; animation-duration: 27s; animation-delay: -12s; }
.hero-floating-particles .particle:nth-child(13) { width: 5px; height: 5px; left: 60%; animation-duration: 16s; animation-delay: -3s; }
.hero-floating-particles .particle:nth-child(14) { width: 3px; height: 3px; left: 75%; animation-duration: 21s; animation-delay: -9s; }
.hero-floating-particles .particle:nth-child(15) { width: 2px; height: 2px; left: 90%; animation-duration: 29s; animation-delay: -14s; }
.hero-floating-particles .particle:nth-child(16) { width: 4px; height: 4px; left: 20%; animation-duration: 23s; animation-delay: -6s; }
.hero-floating-particles .particle:nth-child(17) { width: 3px; height: 3px; left: 35%; animation-duration: 17s; animation-delay: -11s; }
.hero-floating-particles .particle:nth-child(18) { width: 5px; height: 5px; left: 80%; animation-duration: 25s; animation-delay: -16s; }
.hero-floating-particles .particle:nth-child(19) { width: 4px; height: 4px; left: 8%; animation-duration: 22s; animation-delay: -4s; }
.hero-floating-particles .particle:nth-child(20) { width: 2px; height: 2px; left: 18%; animation-duration: 31s; animation-delay: -8s; }
.hero-floating-particles .particle:nth-child(21) { width: 3px; height: 3px; left: 28%; animation-duration: 18s; animation-delay: -13s; }
.hero-floating-particles .particle:nth-child(22) { width: 5px; height: 5px; left: 38%; animation-duration: 26s; animation-delay: -5s; }
.hero-floating-particles .particle:nth-child(23) { width: 4px; height: 4px; left: 48%; animation-duration: 20s; animation-delay: -10s; }
.hero-floating-particles .particle:nth-child(24) { width: 2px; height: 2px; left: 58%; animation-duration: 28s; animation-delay: -15s; }
.hero-floating-particles .particle:nth-child(25) { width: 3px; height: 3px; left: 68%; animation-duration: 17s; animation-delay: -7s; }
.hero-floating-particles .particle:nth-child(26) { width: 5px; height: 5px; left: 78%; animation-duration: 24s; animation-delay: -12s; }
.hero-floating-particles .particle:nth-child(27) { width: 4px; height: 4px; left: 88%; animation-duration: 19s; animation-delay: -9s; }
.hero-floating-particles .particle:nth-child(28) { width: 2px; height: 2px; left: 12%; animation-duration: 30s; animation-delay: -14s; }
.hero-floating-particles .particle:nth-child(29) { width: 3px; height: 3px; left: 22%; animation-duration: 16s; animation-delay: -6s; }
.hero-floating-particles .particle:nth-child(30) { width: 5px; height: 5px; left: 32%; animation-duration: 23s; animation-delay: -11s; }
.hero-floating-particles .particle:nth-child(31) { width: 4px; height: 4px; left: 42%; animation-duration: 21s; animation-delay: -8s; }
.hero-floating-particles .particle:nth-child(32) { width: 2px; height: 2px; left: 52%; animation-duration: 27s; animation-delay: -13s; }
.hero-floating-particles .particle:nth-child(33) { width: 3px; height: 3px; left: 62%; animation-duration: 18s; animation-delay: -5s; }
.hero-floating-particles .particle:nth-child(34) { width: 5px; height: 5px; left: 72%; animation-duration: 25s; animation-delay: -10s; }
.hero-floating-particles .particle:nth-child(35) { width: 4px; height: 4px; left: 82%; animation-duration: 20s; animation-delay: -15s; }
.hero-floating-particles .particle:nth-child(36) { width: 2px; height: 2px; left: 92%; animation-duration: 29s; animation-delay: -7s; }
.hero-floating-particles .particle:nth-child(37) { width: 3px; height: 3px; left: 6%; animation-duration: 22s; animation-delay: -12s; }
.hero-floating-particles .particle:nth-child(38) { width: 5px; height: 5px; left: 16%; animation-duration: 17s; animation-delay: -9s; }
.hero-floating-particles .particle:nth-child(39) { width: 4px; height: 4px; left: 26%; animation-duration: 24s; animation-delay: -14s; }
.hero-floating-particles .particle:nth-child(40) { width: 2px; height: 2px; left: 36%; animation-duration: 19s; animation-delay: -6s; }
.hero-floating-particles .particle:nth-child(41) { width: 3px; height: 3px; left: 46%; animation-duration: 26s; animation-delay: -11s; }
.hero-floating-particles .particle:nth-child(42) { width: 5px; height: 5px; left: 56%; animation-duration: 21s; animation-delay: -8s; }
.hero-floating-particles .particle:nth-child(43) { width: 4px; height: 4px; left: 66%; animation-duration: 28s; animation-delay: -13s; }
.hero-floating-particles .particle:nth-child(44) { width: 2px; height: 2px; left: 76%; animation-duration: 18s; animation-delay: -5s; }
.hero-floating-particles .particle:nth-child(45) { width: 3px; height: 3px; left: 86%; animation-duration: 23s; animation-delay: -10s; }
.hero-floating-particles .particle:nth-child(46) { width: 5px; height: 5px; left: 96%; animation-duration: 20s; animation-delay: -15s; }
.hero-floating-particles .particle:nth-child(47) { width: 4px; height: 4px; left: 2%; animation-duration: 25s; animation-delay: -7s; }
.hero-floating-particles .particle:nth-child(48) { width: 2px; height: 2px; left: 98%; animation-duration: 16s; animation-delay: -12s; }


.hero-glow {
  display: block !important;
  position: absolute;
  top: 50%;
  left: 50%;
  width: 800px;
  height: 800px;
  background: radial-gradient(circle, rgba(29, 78, 216, 0.1) 0%, transparent 60%);
  transform: translate(-50%, -50%);
  filter: blur(100px);
  pointer-events: none;
  z-index: 0;
}

.hero-content {
  position: relative;
  z-index: 10;
  text-align: center;
  max-width: 1000px;
  animation: heroContentSlideUp 1s ease-out;
  margin: 45px 0 0 0;
  padding: 0;
}

.hero-title {
  font-size: clamp(3rem, 6vw, 5rem);
  font-weight: 900;
  margin-bottom: 0.7rem;
  color: #fff;
  background: none;
  -webkit-background-clip: unset;
  -webkit-text-fill-color: unset;
  background-clip: unset;
  text-align: center;
  position: relative;
  animation: fadeInUp 0.8s ease-out 0.2s both;
  text-shadow: none;
  letter-spacing: -0.02em;
  line-height: 1.1;
  font-family: 'Inter', 'Georgia', serif;
}

.hero-title::before {
  display: none;
}

.hero-dna-icon {
  font-size: 1.2rem;
  margin-right: 0.7rem;
  animation: none;
  display: inline-block;
  opacity: 0.7;
}

.hero-subtitle {
  font-size: clamp(1.125rem, 3vw, 1.5rem);
  font-weight: 500;
  opacity: 0.92;
  text-align: center;
  max-width: 800px;
  margin: 0 auto 2.5rem;
  line-height: 1.7;
  position: relative;
  animation: fadeInUp 0.8s ease-out 0.4s both;
  text-shadow: none;
  color: #e5e7eb;
}

.hero-features {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  max-width: 900px;
  margin: 2.5rem auto 0;
  animation: fadeInUp 0.8s ease-out 0.6s both;
  justify-content: center;
}

.hero-feature {
  background: #fff;
  border: 1.5px solid #011f5b;
  border-radius: var(--radius-xl);
  padding: 1.5rem 1.5rem 1.2rem 1.5rem;
  text-align: center;
  transition: var(--transition-slow);
  box-shadow: 0 2px 8px rgba(1,31,91,0.07);
  min-width: 220px;
  max-width: 270px;
  color: #011f5b;
}

.hero-feature:hover {
  transform: translateY(-4px);
  background: #f3f4f6;
  box-shadow: 0 4px 16px rgba(1,31,91,0.12);
}

.hero-feature-icon {
  font-size: 2.5rem;
  margin-bottom: 0.7rem;
  display: block;
  opacity: 1;
  animation: none;
  color: #011f5b !important;
}

.hero-feature-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.7rem;
  color: #011f5b;
}

.hero-feature-description {
  font-size: 0.95rem;
  color: #374151;
  line-height: 1.5;
}

.hero-cta {
  margin-top: 4.5rem;
  animation: fadeInUp 0.8s ease-out 0.8s both;
}

.hero-cta-button {
  background: #011f5b;
  color: #fff;
  border: 2px solid #011f5b;
  border-radius: 50px;
  padding: 1.1rem 2.5rem;
  font-weight: 800;
  font-size: 1.1rem;
  cursor: pointer;
  transition: var(--transition-bounce);
  box-shadow: 0 4px 16px rgba(1,31,91,0.10);
  text-transform: uppercase;
  letter-spacing: 1px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 1rem;
}

.hero-cta-button:hover {
  background: #001127;
  color: #fff;
  border-color: #001127;
  transform: translateY(-2px) scale(1.03);
  box-shadow: 0 8px 32px rgba(1,31,91,0.18);
}

.hero-cta-button::after {
  content: '↓';
  font-size: 1.2rem;
  transition: var(--transition-base);
}

.hero-cta-button:hover::after {
  transform: translateY(5px);
}

@media (max-width: 768px) {
  .hero-section {
    padding-top: 100px;
    min-height: 100vh;
  }
  .hero-title {
    font-size: clamp(2rem, 8vw, 3rem);
    margin-bottom: 0.5rem;
    letter-spacing: -0.01em;
  }
  .hero-features {
    flex-direction: column;
    gap: 1rem;
    margin: 1.5rem auto 0;
  }
  .hero-feature {
    padding: 1.2rem;
    min-width: 0;
    max-width: 100%;
  }
}

/* Modern Cards */
.query-card {
  background: var(--bg-gradient-card);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-2xl);
  padding: 2.5rem;
  box-shadow: var(--shadow-xl);
  margin-bottom: 3rem;
  animation: fadeInUp 0.6s ease-out 0.6s both;
  transition: var(--transition-slow);
}

.query-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-2xl);
}

.report-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-2xl);
  padding: 0;
  box-shadow: var(--shadow-2xl);
  margin-top: 3rem;
  overflow: hidden;
  animation: fadeInScale 0.6s ease-out;
}

/* Report Header */
.report-header {
  background: var(--bg-gradient-primary);
  color: white;
  padding: 3rem 2rem;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.report-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="0.5"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
  pointer-events: none;
}

/* Modern Input Styling */
.modern-input {
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid var(--gray-200);
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
  font-size: 1rem;
  font-weight: 500;
  transition: var(--transition-base);
  backdrop-filter: blur(10px);
}

.modern-input:focus {
  outline: none;
  border-color: var(--primary-600);
  background: rgba(255, 255, 255, 1);
  box-shadow: 0 0 0 4px rgba(1, 31, 91, 0.1);
  transform: translateY(-1px);
}

/* Enhanced Button Styling */
.modern-button {
  background: var(--bg-gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  padding: 1rem 2.5rem;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: var(--transition-bounce);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.modern-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transition: var(--transition-slow);
}

.modern-button:hover {
  transform: translateY(-3px) scale(1.02);
  box-shadow: var(--shadow-2xl);
}

.modern-button:hover::before {
  left: 100%;
}

.modern-button:active {
  transform: translateY(-1px) scale(0.98);
}

/* Top Navigation Bar Styling */
.top-navbar {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: var(--shadow-sm);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2000;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  transition: var(--transition-base);
}

.top-navbar.scrolled {
  background: rgba(255, 255, 255, 0.98);
  box-shadow: var(--shadow-md);
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-decoration: none;
  color: var(--primary-900);
  font-weight: 900;
  font-size: 1.3rem;
  transition: var(--transition-base);
}

.navbar-brand:hover {
  transform: scale(1.05);
  color: var(--primary-700);
}

.navbar-brand-link {
  text-decoration: none;
  color: var(--primary-900);
  font-weight: 900;
  font-size: 1.5rem;
  transition: var(--transition-base);
  cursor: pointer;
}

.navbar-brand-link:hover {
  transform: scale(1.05);
  color: var(--primary-700);
  text-decoration: none;
}

.navbar-brand-icon {
  font-size: 1.7rem;
  background: var(--bg-gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.navbar-nav {
  display: flex;
  align-items: center;
  gap: 2.5rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-item {
  position: relative;
}

.nav-link {
  color: var(--gray-700);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.95rem;
  padding: 0.75rem 0;
  transition: var(--transition-base);
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--primary-600);
  transition: var(--transition-base);
}

.nav-link:hover {
  color: var(--primary-600);
  transform: translateY(-1px);
}

.nav-link:hover::after {
  width: 100%;
}

.nav-link.active {
  color: var(--primary-600);
}

.nav-link.active::after {
  width: 100%;
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.nav-button {
  background: transparent;
  border: 2px solid var(--primary-600);
  color: var(--primary-600);
  border-radius: var(--radius-lg);
  padding: 0.625rem 1.5rem;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: var(--transition-base);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-button:hover {
  background: var(--primary-600);
  color: white;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.nav-button.primary {
  background: #021f5b;
  color: white;
  border-color: transparent;
}

.nav-button.primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* Mobile Navigation */
.mobile-toggle {
  display: none;
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--primary-600);
  cursor: pointer;
  padding: 0.5rem;
}

.mobile-nav {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--gray-200);
  box-shadow: var(--shadow-lg);
  padding: 1rem 2rem 2rem;
}

.mobile-nav .navbar-nav {
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.mobile-nav .navbar-actions {
  flex-direction: column;
  gap: 1rem;
  width: 100%;
}

.mobile-nav .nav-button {
  width: 100%;
  justify-content: center;
}

/* Responsive Mobile Menu */
@media (max-width: 768px) {
  .navbar-nav {
    display: none;
  }
  
  .navbar-actions {
    display: none;
  }
  
  .mobile-toggle {
    display: block;
  }
  
  .mobile-nav.show {
    display: block;
  }
  
  .top-navbar {
    padding: 0 1rem;
  }
}

/* Body padding to account for fixed navbar */
body {
  padding-top: 0;
}

/* Status Cards */
.status-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-xl);
  padding: 1.5rem 2rem;
  margin: 1rem 0;
  box-shadow: var(--shadow-md);
  animation: slideInRight 0.4s ease-out;
  transition: var(--transition-base);
}

.status-card:hover {
  transform: translateX(5px);
  box-shadow: var(--shadow-lg);
}

/* Info Cards with Enhanced Styling */
.info-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-xl);
  padding: 2rem;
  margin: 1.5rem 0;
  box-shadow: var(--shadow-sm);
  transition: var(--transition-slow);
  position: relative;
  overflow: hidden;
}

.info-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--bg-gradient-primary); /* Changed to use gradient */
  transition: var(--transition-base);
  transform: scaleY(0);
  transform-origin: top;
}

.info-card.genetic-risk::before {
  background: var(--primary-600);
}

.info-card.integrated-risk::before {
  background: var(--primary-700);
}

.info-card.phewas::before {
  background: var(--accent-500);
}

.info-card.warning::before {
  background: var(--warning-500);
}

.info-card.error::before {
  background: var(--error-500);
}

.info-card:hover::before {
  transform: scaleY(1);
}

.info-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

.info-card.genetic-risk {
  border-left: 5px solid var(--primary-600);
  background: linear-gradient(135deg, var(--primary-50) 0%, rgba(255,255,255,0.8) 100%);
}

.info-card.integrated-risk {
  border-left: 5px solid var(--primary-700);
  background: linear-gradient(135deg, var(--primary-100) 0%, rgba(255,255,255,0.8) 100%);
}

.info-card.phewas {
  border-left: 5px solid var(--accent-500);
  background: linear-gradient(135deg, #f0fdf4 0%, rgba(255,255,255,0.8) 100%);
}

.info-card.warning {
  border-left: 5px solid var(--warning-500);
  background: linear-gradient(135deg, #fffbeb 0%, rgba(255,255,255,0.8) 100%);
}

.info-card.error {
  border-left: 5px solid var(--error-500);
  background: linear-gradient(135deg, #fef2f2 0%, rgba(255,255,255,0.8) 100%);
}

.info-card.genetic-risk .highlight-box {
  border-left: 4px solid var(--primary-600) !important;
}

.info-card.integrated-risk .highlight-box {
  border-left: 4px solid var(--primary-700) !important;
}

.info-card.phewas .highlight-box {
  border-left: 4px solid var(--accent-500) !important;
}

.info-card.warning .highlight-box {
  border-left: 4px solid var(--warning-500) !important;
}

  .info-card.error .highlight-box {
    border-left: 4px solid var(--error-500) !important;
  }

/* Enhanced Card Header Styles (matching dashboard.py style) */
.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
}

.card-icon-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 60px;
  height: 60px;
  background-color: #eef2ff;
  border-radius: 50%;
  margin-right: 1rem;
  flex-shrink: 0;
}

.card-icon {
  font-size: 2.25rem;
  color: #011f5b;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 800;
  color: #1e293b;
  margin: 0;
}

.card-description {
  font-size: 0.95rem;
  color: #475569;
  line-height: 1.6;
  flex-grow: 1;
}

/* Step Card Styles (matching dashboard.py) */
.step-card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0,0,0,0.05), 0 10px 20px rgba(0,0,0,0.05);
  border: 1px solid #e2e8f0;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.step-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 15px rgba(0,0,0,0.07), 0 15px 30px rgba(0,0,0,0.07);
}

/* Metric Card Styles */
.metric-card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  text-align: center;
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.metric-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--primary-900);
  margin-bottom: 0.5rem;
}

.metric-label {
  font-size: 0.875rem;
  color: var(--gray-600);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Enhanced Button Styles */
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
  margin-bottom: 1rem;
  background-color: #eef2ff;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mode-card .card-icon-wrapper .material-symbols-outlined {
  font-size: 2.5rem;
  color: #011f5b;
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

/* Responsive Agent Layout */
@media (max-width: 1024px) {
  .agent-layout {
    flex-direction: column !important;
    height: auto !important;
  }

  .agent-layout > div:first-child {
    flex: none !important;
    height: 40vh !important;
  }

  .agent-layout > div:last-child {
    flex: none !important;
    height: 50vh !important;
  }
}

@media (max-width: 768px) {
  .agent-layout {
    flex-direction: column !important;
    height: auto !important;
  }

  .agent-layout > div:first-child,
  .agent-layout > div:last-child {
    flex: none !important;
    height: 45vh !important;
  }
}

/* Modern Tabs */
.modern-tabs {
  background: var(--gray-100);
  border-radius: var(--radius-xl);
  padding: 0.75rem;
  margin: 2rem 0;
  box-shadow: var(--shadow-sm);
}

.modern-tab {
  background: transparent;
  border: none;
  border-radius: var(--radius-lg);
  padding: 1rem 2rem;
  font-weight: 600;
  font-size: 0.95rem;
  transition: var(--transition-base);
  cursor: pointer;
  color: var(--gray-600);
  position: relative;
}

.modern-tab:hover {
  background: rgba(255, 255, 255, 0.7);
  color: var(--primary-700);
}

.modern-tab.active {
  background: white;
  color: var(--primary-900);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

/* Section Titles */
.section-title {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--primary-900);
  margin-bottom: 2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  position: relative;
}

.section-title::before {
  content: '';
  width: 6px;
  height: 2rem;
  background: var(--bg-gradient-primary); /* Already using gradient, confirmed */
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
}

/* Plot Containers */
.plot-container {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-xl);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);
  overflow: hidden;
}

.plot-container:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* Enhanced Loading Spinner */
.loading-spinner {
  display: inline-block;
  width: 2rem;
  height: 2rem;
  border: 3px solid var(--primary-200);
  border-radius: 50%;
  border-top-color: var(--primary-900);
  animation: spin 1s linear infinite;
  box-shadow: var(--shadow-sm);
}

/* Badges */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);
}

.badge:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
}

.badge.primary {
  background: var(--primary-900);
  color: white;
}

.badge.success {
  background: var(--accent-500);
  color: white;
}

.badge.warning {
  background: var(--warning-500);
  color: white;
}

.badge.error {
  background: var(--error-500);
  color: white;
}

/* Highlight Boxes */
.highlight-box {
  background: linear-gradient(135deg, rgba(1, 31, 91, 0.03) 0%, rgba(59, 130, 246, 0.03) 100%);
  border: 1px solid rgba(1, 31, 91, 0.1);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  margin: 1rem 0;
  transition: var(--transition-base);
  position: relative;
  overflow: hidden;
}

.highlight-box:hover {
  background: linear-gradient(135deg, rgba(1, 31, 91, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%);
  border-color: rgba(1, 31, 91, 0.2);
  transform: translateX(5px);
}

.highlight-box::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--primary-600);
  transition: var(--transition-base);
  transform: scaleY(0);
}

.highlight-box:hover::before {
  transform: scaleY(1);
  }

  /* Enhanced Responsive Design */
@media (max-width: 768px) {
  .hero-section {
    /* Full screen hero section */
    padding-top: 100px;
    min-height: 100vh;
  }
  
  .hero-badge {
    font-size: 0.8rem;
    padding: 0.6rem 1.5rem;
    margin-bottom: 2rem;
  }
  
  .hero-title {
    font-size: clamp(2rem, 8vw, 3rem);
    margin-bottom: 0.5rem;
    letter-spacing: -0.01em;
  }
  
  .hero-dna-icon {
    font-size: 1.2rem;
  }
  
  .hero-subtitle {
    font-size: clamp(1rem, 4vw, 1.25rem);
    line-height: 1.6;
    margin-bottom: 2rem;
  }
  
  .hero-features {
    grid-template-columns: 1fr;
    gap: 1.5rem;
    margin: 2rem auto 0;
  }
  
  .hero-feature {
    padding: 1.5rem;
  }
  
  .hero-feature-icon {
    font-size: 2rem;
  }
  
  .hero-feature-title {
    font-size: 1.1rem;
  }
  
  .hero-feature-description {
    font-size: 0.9rem;
  }
  
  .hero-cta {
    margin-top: 4.5rem;
  }
  
  .hero-cta-button {
    padding: 1rem 2rem;
    font-size: 1rem;
  }
}

  .query-card {
    padding: 1.5rem;
    margin: 0 0.5rem 2rem;
  }
  
  .report-card {
    margin: 1rem 0.5rem;
  }
  
  .info-card {
    padding: 1.25rem;
    margin: 1rem 0;
  }
  
  .info-card .highlight-box {
    font-size: 0.85rem;
    padding: 0.8rem;
  }

  .section-title {
    font-size: 1.5rem;
  }
  
  .modern-button {
    padding: 0.875rem 2rem;
    font-size: 0.9rem;
  }
  
  .plot-container {
    padding: 1rem;
  }

  /* Add specific style for responsive table overflow */
  .q-table__container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Focus indicators */
*:focus-visible {
  outline: 2px solid var(--primary-600);
  outline-offset: 2px;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: var(--gray-100);
  border-radius: var(--radius-sm);
}

::-webkit-scrollbar-thumb {
  background: var(--primary-900);
  border-radius: var(--radius-sm);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--primary-950);
}

/* Enhanced Table Styling */
.modern-table .q-table__container {
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

/* Upload Area State Transitions */
#agent-upload-area, #manual-upload-area {
  transition: all 0.3s ease;
}

#agent-upload-area.uploaded, #manual-upload-area.uploaded {
  border-color: #6b7280 !important;
  background: rgba(107, 114, 128, 0.1) !important;
  cursor: default !important;
}

#agent-upload-area.uploaded #agent-upload-content,
#manual-upload-area.uploaded #manual-upload-content {
  background: rgba(107, 114, 128, 0.1) !important;
}

/* Delete Button Styling */
.upload-delete-btn {
  background: #ef4444 !important;
  color: white !important;
  border: none !important;
  border-radius: 50% !important;
  width: 24px !important;
  height: 24px !important;
  cursor: pointer !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 0.8rem !important;
  transition: all 0.2s ease !important;
}

.upload-delete-btn:hover {
  background: #dc2626 !important;
  transform: scale(1.1) !important;
}

/* Data Preview Container Styling */
.data-preview-container {
  scrollbar-width: thin;
  scrollbar-color: var(--primary-900) var(--gray-200);
}

.data-preview-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.data-preview-container::-webkit-scrollbar-track {
  background: var(--gray-100);
  border-radius: var(--radius-sm);
}

.data-preview-container::-webkit-scrollbar-thumb {
  background: var(--primary-900);
  border-radius: var(--radius-sm);
}

.data-preview-container::-webkit-scrollbar-thumb:hover {
  background: var(--primary-950);
}

.data-preview-container::-webkit-scrollbar-corner {
  background: var(--gray-100);
}

.modern-table thead {
  background: var(--primary-900);
  color: white;
  font-weight: 700;
}

.modern-table thead th {
  padding: 1rem 1.5rem;
  text-align: left;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.modern-table tbody tr:nth-child(odd) {
  background-color: var(--gray-50); /* Zebra striping */
}

.modern-table tbody tr:hover {
  background-color: var(--primary-50);
  transition: var(--transition-fast);
}

.modern-table tbody td {
  padding: 1rem 1.5rem;
  font-size: 0.9rem;
  color: var(--gray-800);
}
</style>

<script>
// Enhanced navigation functionality
document.addEventListener('DOMContentLoaded', function() {
    const navbar = document.querySelector('.top-navbar');
    const navLinks = document.querySelectorAll('.nav-link');
    const mobileToggle = document.querySelector('.mobile-toggle');
    const mobileNav = document.querySelector('.mobile-nav');
    
    // Scroll effect for navbar
    let isScrolled = false;
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        if (scrollTop > 50 && !isScrolled) {
            navbar.classList.add('scrolled');
            isScrolled = true;
        } else if (scrollTop <= 50 && isScrolled) {
            navbar.classList.remove('scrolled');
            isScrolled = false;
        }
    });
    
    // Enhanced smooth scrolling for ALL anchor links with precise positioning
    function setupSmoothScrolling(links) {
        links.forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href && href.startsWith('#')) {
                    e.preventDefault();

                    // Special handling for brand link (href="#") - scroll to top
                    if (href === '#') {
                        window.scrollTo({
                            top: 0,
                            behavior: 'smooth'
                        });
                        // Close mobile menu if open
                        if (mobileNav && mobileNav.classList.contains('show')) {
                            mobileNav.classList.remove('show');
                        }
                        return;
                    }

                    const target = document.querySelector(href);
                    if (target) {
                        // Calculate precise scroll position with responsive navbar offset
                        const navbar = document.querySelector('.top-navbar');
                        let navbarHeight = navbar ? navbar.offsetHeight : 60;
                        let additionalPadding = 20;

                        // Adjust for mobile devices
                        if (window.innerWidth <= 768) {
                            // On mobile, account for any additional spacing
                            additionalPadding = 30;
                        }

                        // Special handling for hero section to ensure proper positioning
                        if (href === '#mode-selection') {
                            additionalPadding = 40; // Extra space for better visibility
                        }

                        const targetRect = target.getBoundingClientRect();
                        const offsetTop = window.pageYOffset + targetRect.top - navbarHeight - additionalPadding;

                        window.scrollTo({
                            top: Math.max(0, offsetTop), // Ensure we don't scroll to negative positions
                            behavior: 'smooth'
                        });
                    }

                    // Update active nav link if this is a nav link
                    if (this.classList.contains('nav-link')) {
                        navLinks.forEach(l => l.classList.remove('active'));
                        this.classList.add('active');

                        // Close mobile menu if open
                        if (mobileNav && mobileNav.classList.contains('show')) {
                            mobileNav.classList.remove('show');
                        }
                    }
                }
            });
        });
    }

    // Apply smooth scrolling to navigation links
    setupSmoothScrolling(navLinks);

    // Apply smooth scrolling to ALL anchor links with hash hrefs (including CTA buttons)
    const allAnchorLinks = document.querySelectorAll('a[href^="#"]');
    setupSmoothScrolling(allAnchorLinks);
    
    // Mobile menu toggle
    if (mobileToggle && mobileNav) {
        mobileToggle.addEventListener('click', function() {
            mobileNav.classList.toggle('show');
        });
        
        // Close mobile menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!navbar.contains(e.target)) {
                mobileNav.classList.remove('show');
            }
        });
    }
    
    // Intersection Observer for section highlighting with improved precision
    const sections = document.querySelectorAll('section[id], div[id]');
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '-100px 0px -70% 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.getAttribute('id');
                if (id) {
                    navLinks.forEach(link => {
                        link.classList.remove('active');
                        if (link.getAttribute('href') === '#' + id) {
                            link.classList.add('active');
                        }
                    });
                }
            }
        });
    }, observerOptions);
    
    sections.forEach(section => {
        observer.observe(section);
    });
    
    // Add smooth reveal animations
    const animateOnScroll = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });
    
    // Apply to cards and sections
    document.querySelectorAll('.query-card, .report-card, .info-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        animateOnScroll.observe(el);
    });
});

    // Add keyboard navigation support
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const mobileNav = document.querySelector('.mobile-nav');
            if (mobileNav && mobileNav.classList.contains('show')) {
                mobileNav.classList.remove('show');
            }
        }
    });

    // Function to reset agent upload area
    window.resetAgentUpload = function() {
        const uploadArea = document.getElementById('agent-upload-area');
        const uploadContent = document.getElementById('agent-upload-content');
        if (uploadArea && uploadContent) {
            uploadArea.classList.remove('uploaded');
            uploadContent.innerHTML = `
                <span class="material-symbols-outlined" style="font-size: 1.2rem; margin-bottom: 0.25rem; display: block;">upload_file</span>
                <div style="font-weight: 600; font-size: 0.8rem;">Upload CSV</div>
                <div style="font-size: 0.7rem; color: var(--gray-600); margin-top: 0.1rem;">Click or drag file</div>
            `;
        }
        // Clear the file input
        const fileInput = uploadArea.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.value = '';
        }
        // Clear data preview
        const previewContainer = document.querySelector('.data-preview-container');
        if (previewContainer) {
            previewContainer.innerHTML = `
                <div style="text-align: center; color: var(--gray-600); padding: 1rem;">
                    <span class="material-symbols-outlined" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block;">description</span>
                    <div style="font-weight: 600; margin-bottom: 0.5rem; font-size: 0.9rem;">No Data Uploaded</div>
                    <div style="font-size: 0.8rem;">Click above to upload CSV file</div>
                </div>
            `;
        }
        // Clear global file ID
        window.currentAgentFileId = null;
        // Trigger Python-side reset
        if (window.pyodide && window.pyodide.runPython) {
            window.pyodide.runPython('reset_agent_upload_state()');
        }
    };

    // Function to reset manual upload area
    window.resetManualUpload = function() {
        const uploadArea = document.getElementById('manual-upload-area');
        const uploadContent = document.getElementById('manual-upload-content');
        if (uploadArea && uploadContent) {
            uploadArea.classList.remove('uploaded');
            uploadContent.innerHTML = `
                <span style="color: #fff; font-weight: 600;">Click to Upload CSV</span>
            `;
        }
        // Clear the file input
        const fileInput = uploadArea.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.value = '';
        }
        // Update status text
        const statusElement = document.getElementById('file-status');
        if (statusElement) {
            statusElement.textContent = 'No file selected';
        }
        // Clear uploaded state in Python
        // Since we can't directly call Python from JS, we'll handle this in the upload function
    };
</script>
''')

async def create_job_async(file_name: str, file_bytes: bytes, bigbetter: bool, B: int, seed: int):
    """Create a ranking job by uploading CSV and parameters."""
    url = f'{API_BASE}/jobs'
    logger.info(f"Creating ranking job: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('file', file_bytes, filename=file_name or 'data.csv', content_type='text/csv')
            form.add_field('bigbetter', 'true' if bigbetter else 'false')
            form.add_field('B', str(B))
            form.add_field('seed', str(seed))
            async with session.post(url, data=form, timeout=60) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('job_id'), None
                error_text = await resp.text()
                return None, f'API error: {resp.status} - {error_text}'
    except asyncio.TimeoutError:
        return None, 'Request timeout - please try again'
    except Exception as e:
        return None, f'Connection error: {str(e)}'

async def poll_status_async(job_id: str, timeout_sec: int = 600, interval_sec: float = 1.5):
    """Poll job status until completion or timeout."""
    url = f'{API_BASE}/jobs/{job_id}/status'
    logger.info(f"Polling status for job: {job_id}")
    start = asyncio.get_event_loop().time()
    try:
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(url, timeout=30) as resp:
                    data = await resp.json()
                    status = data.get('status')
                    if status in ('succeeded', 'failed'):
                        return data
                await asyncio.sleep(interval_sec)
                if asyncio.get_event_loop().time() - start > timeout_sec:
                    return {'job_id': job_id, 'status': 'failed', 'message': 'Timeout waiting for job'}
    except Exception as e:
        return {'job_id': job_id, 'status': 'failed', 'message': f'Polling error: {str(e)}'}

async def fetch_results_async(job_id: str):
    """Fetch results JSON for a finished job."""
    url = f'{API_BASE}/jobs/{job_id}/results'
    logger.info(f"Fetching results from: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as resp:
                if resp.status == 200:
                    return await resp.json(), None
                elif resp.status == 202:
                    return None, 'Results not ready'
                else:
                    return None, f'API error: {resp.status} - {await resp.text()}'
    except Exception as e:
        return None, f'Connection error: {str(e)}'

def show_results(result):
    with ui.element('div').classes('report-card').style('max-width: 1400px; margin: 0 auto; width: 100%;'):
        with ui.element('div').classes('report-header'):
            ui.html(f'''
                <div style="position: relative; z-index: 10;">
                    <div class="hero-title" style="font-size: 2.5rem; margin-bottom: 1rem; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <span class="material-symbols-outlined" style="font-size: 2.5rem; margin-right: 0.5rem; vertical-align: middle;">analytics</span> Robust Ranking Report
                    </div>
                    <div style="font-size: 1rem; opacity: 0.9; max-width: 600px; margin: 0 auto; line-height: 1.5;">
                        Vanilla Spectral Method ranking with bootstrap confidence intervals
                    </div>
                </div>
            ''')

        methods = result.get('methods', []) or []
        if not methods:
            with ui.element('div').classes('info-card error'):
                ui.html('<div class="highlight-box">No results available.</div>')
            return

        # Add Analysis Results summary card (shared across modes)
        with ui.element('div').classes('info-card').style('padding: 1.25rem 1.5rem; margin: 1.5rem 1rem;'):
            ui.html('<div class="section-title"><span class="material-symbols-outlined" style="font-size: 1.2rem; margin-right: 0.5rem; vertical-align: middle;">description</span> Analysis Results</div>')
            header = ['Method', 'θ̂', 'Rank', 'CI (Two-Sided)', 'CI Left']
            rows_html = []
            for m in methods[:6]:
                name = m.get('name', '')
                theta = m.get('theta_hat', '')
                rank = m.get('rank', '')
                ci_two = m.get('ci_two_sided') or [None, None]
                ci_left = m.get('ci_left', '')
                ci_disp = f"[{ci_two[0]}, {ci_two[1]}]" if ci_two and len(ci_two) == 2 else 'N/A'
                rows_html.append(f"<tr><td><b>{name}</b></td><td>{theta}</td><td>{rank}</td><td>{ci_disp}</td><td>{ci_left}</td></tr>")
            table_html = (
                '<table style="width:100%; border-collapse: collapse; font-size: 0.9rem;">'
                + '<thead><tr>'
                + ''.join([f'<th style="text-align:left; padding: 8px; border-bottom: 1px solid #e5e7eb;">{h}</th>' for h in header])
                + '</tr></thead><tbody>'
                + ''.join(rows_html)
                + '</tbody></table>'
            )
            ui.html(table_html)

        # Build figures
        names = [m.get('name') for m in methods]
        theta = [m.get('theta_hat') for m in methods]
        ranks = [m.get('rank') for m in methods]
        ci_two = [m.get('ci_two_sided') for m in methods]

        # Sort all data by theta descending for consistent ordering
        sorted_indices = sorted(range(len(theta)), key=lambda i: theta[i])
        names_sorted = [methods[i]['name'] for i in sorted_indices]
        theta_sorted = [methods[i]['theta_hat'] for i in sorted_indices]
        ranks_sorted = [methods[i]['rank'] for i in sorted_indices]
        ci_two_sorted = [methods[i]['ci_two_sided'] for i in sorted_indices]

        # --- 1. Horizontal Bar Chart for Ability Score ---
        theta_fig = go.Figure(go.Bar(
            x=theta_sorted,
            y=names_sorted,
            orientation='h',
            marker_color='rgb(29, 78, 216)'
        ))
        theta_fig.update_layout(
            title='<b>Ability Score (theta.hat)</b><br><span style="font-size:0.8em;color:grey;">Methods are ranked based on this score.</span>',
            xaxis_title='Theta Score (Higher is Better)',
            yaxis_title='',
            plot_bgcolor='white',
            margin=dict(l=20, r=20, t=50, b=20), # Increased top margin for subtitle
        )

        # --- 2. Dumbbell Plot for Rank with CI ---
        ci_left = [c[0] if c and len(c) == 2 else r for c, r in zip(ci_two_sorted, ranks_sorted)]
        ci_right = [c[1] if c and len(c) == 2 else r for c, r in zip(ci_two_sorted, ranks_sorted)]

        rank_fig = go.Figure()

        # Add lines for the CI ranges (the "dumbbell" bar)
        for i, name in enumerate(names_sorted):
            rank_fig.add_shape(
                type="line",
                x0=ci_left[i], y0=name,
                x1=ci_right[i], y1=name,
                line=dict(color="lightgrey", width=2)
            )

        # Add scatter points for the CI endpoints
        rank_fig.add_trace(go.Scatter(
            x=ci_left, y=names_sorted,
            mode='markers',
            marker=dict(color='grey', size=8),
            name='CI Lower Bound',
            hoverinfo='none'
        ))
        rank_fig.add_trace(go.Scatter(
            x=ci_right, y=names_sorted,
            mode='markers',
            marker=dict(color='grey', size=8),
            name='CI Upper Bound',
            hoverinfo='none'
        ))
        
        # Add scatter points for the actual rank
        rank_fig.add_trace(go.Scatter(
            x=ranks_sorted, y=names_sorted,
            mode='markers',
            marker=dict(color='rgb(16, 185, 129)', size=10, symbol='diamond'),
            name='Estimated Rank',
            hovertemplate='<b>%{y}</b><br>Rank: %{x}<br>95% CI: [%{customdata[0]}, %{customdata[1]}]<extra></extra>',
            customdata=list(zip(ci_left, ci_right))
        ))

        rank_fig.update_layout(
            title='<b>Rank with 95% Confidence Interval</b><br><span style="font-size:0.8em;color:grey;">Based on Ability Score, where Rank 1 is the best.</span>',
            xaxis_title='Rank',
            yaxis_title='',
            plot_bgcolor='white',
            showlegend=False,
            xaxis_autorange='reversed',
            margin=dict(l=20, r=20, t=50, b=20) # Increased top margin for subtitle
        )

        with ui.element('div').classes('info-card').style('padding: 2rem;'):
            with ui.element('div').classes('card-header'):
                with ui.element('div').classes('card-icon-container'):
                    ui.html('<span class="material-symbols-outlined card-icon">calculate</span>')
                ui.html('<h3 class="card-title">Analysis Summary</h3>')
            meta = result.get('metadata', {})
            ui.html(f'<div class="highlight-box">n={meta.get("n_samples", "-")}, k={meta.get("k_methods", "-")}, runtime={meta.get("runtime_sec", "-")}s, B={result.get("params",{}).get("B","-")}</div>')

        # --- Plot Containers ---
        with ui.row().classes('w-full gap-6 no-wrap'):
            with ui.element('div').classes('plot-container w-1/2'):
                theta_plot = ui.plotly(theta_fig).classes('w-full')
            
            with ui.element('div').classes('plot-container w-1/2'):
                rank_plot = ui.plotly(rank_fig).classes('w-full')

        # Table
        rows = []
        for m in methods:
            rows.append({
                'Method': m.get('name'),
                'theta_hat': m.get('theta_hat'),
                'rank': m.get('rank'),
                'ci_two_left': (m.get('ci_two_sided') or [None, None])[0],
                'ci_two_right': (m.get('ci_two_sided') or [None, None])[1],
                'ci_left': m.get('ci_left'),
                'ci_uniform_left': m.get('ci_uniform_left'),
            })
        if rows:
            with ui.element('div').classes('info-card').style('padding: 1rem 2rem 2rem;'):
                with ui.element('div').classes('card-header'):
                    with ui.element('div').classes('card-icon-container'):
                        ui.html('<span class="material-symbols-outlined card-icon">description</span>')
                    ui.html('<h3 class="card-title">Detailed Results</h3>')
                ui.html('<p class="card-description">Comprehensive ranking results with confidence intervals and statistical metrics</p>')
                columns = [
                    {'name': 'Method', 'label': 'Method', 'field': 'Method', 'sortable': True},
                    {'name': 'theta_hat', 'label': 'theta.hat', 'field': 'theta_hat', 'sortable': True},
                    {'name': 'rank', 'label': 'Rank', 'field': 'rank', 'sortable': True},
                    {'name': 'ci_two_left', 'label': 'CI Left', 'field': 'ci_two_left', 'sortable': True},
                    {'name': 'ci_two_right', 'label': 'CI Right', 'field': 'ci_two_right', 'sortable': True},
                    {'name': 'ci_left', 'label': 'Left-sided CI', 'field': 'ci_left', 'sortable': True},
                    {'name': 'ci_uniform_left', 'label': 'Uniform Left CI', 'field': 'ci_uniform_left', 'sortable': True},
                ]
                results_table = ui.table(columns=columns, rows=rows, row_key='Method', pagination=10).classes('w-full modern-table')
        
        # --- Interactivity ---
        def handle_hover(e):
            if e.args and 'points' in e.args and e.args['points']:
                point = e.args['points'][0]
                method_name = point.get('y')
                if method_name and method_name in names_sorted:
                    # Highlight table row
                    results_table.selected = [method_name]
                    
                    # Get index for highlighting
                    idx = names_sorted.index(method_name)
                    
                    # Highlight theta plot by updating trace colors
                    colors = ['rgb(29, 78, 216)'] * len(names_sorted)
                    colors[idx] = 'rgb(245, 158, 11)' # Highlight color
                    theta_plot.figure.update_traces(marker_color=colors)
                    
                    # Highlight rank plot by updating marker size
                    sizes = [10] * len(names_sorted)
                    sizes[idx] = 18 # Emphasize the diamond
                    rank_plot.figure.update_traces(marker_size=sizes, selector=dict(name='Estimated Rank'))
        
        def handle_unhover(e):
            results_table.selected = []
            
            # Restore original colors and sizes directly
            theta_plot.figure.update_traces(marker_color='rgb(29, 78, 216)')
            rank_plot.figure.update_traces(marker_size=10, selector=dict(name='Estimated Rank'))

        theta_plot.on('plotly_hover', handle_hover)
        theta_plot.on('plotly_unhover', handle_unhover)
        rank_plot.on('plotly_hover', handle_hover)
        rank_plot.on('plotly_unhover', handle_unhover)

# Agent Mode Functions
def handle_enter_key(e, input_field, messages_container, status_area, send_button):
    """Handle Enter key press to send message"""
    if e.args and e.args.get('key') == 'Enter' and not e.args.get('shiftKey'):
        # Prevent default behavior by triggering the send button click
        # For HTML button, use JavaScript click with the button ID
        ui.run_javascript('document.getElementById("send-button").click()')

async def handle_agent_file_upload(e, messages_container, input_field):
    """Enhanced file upload handling with better validation and user feedback"""
    # Validate file type
    if not e.name or not e.name.lower().endswith('.csv'):
        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Please upload a CSV file only.')
        return

    # Validate file size (client-side check)
    content = e.content.read() if hasattr(e.content, 'read') else e.content
    if hasattr(content, 'seek'):
        content.seek(0, 2)  # Seek to end
        file_size = content.tell()
        content.seek(0)  # Reset to beginning
    else:
        file_size = len(content)

    if file_size > 50 * 1024 * 1024:  # 50MB limit
        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> File is too large (>50MB). Please use a smaller CSV file.')
        return

    if file_size == 0:
        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> File appears to be empty. Please check your CSV file.')
        return

    # Show uploading state
    ui.run_javascript(f'''
        const uploadArea = document.getElementById('agent-upload-area');
        const uploadContent = document.getElementById('agent-upload-content');
        if (uploadArea && uploadContent) {{
            uploadArea.classList.add('uploaded');
            uploadContent.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                    <span style="font-size: 1.2rem;">⏳</span>
                    <div style="text-align: left;">
                        <div style="font-weight: 600; font-size: 0.8rem; color: var(--gray-700);">Uploading...</div>
                        <div style="font-size: 0.7rem; color: var(--gray-500); margin-top: 0.1rem;">{e.name}</div>
                    </div>
                </div>
            `;
        }}
    ''')

    # Upload to agent endpoint with progress feedback
    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field('file', content, filename=e.name or 'data.csv', content_type='text/csv')

            async with session.post(f'{API_BASE_URL}/api/agent/upload', data=form, timeout=60) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    file_id = result.get('file_id')

                    if not file_id:
                        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Upload failed: No file ID returned from server.')
                        ui.run_javascript('resetAgentUpload();')
                        return

                    # Update upload area to show success state
                    ui.run_javascript(f'''
                        const uploadArea = document.getElementById('agent-upload-area');
                        const uploadContent = document.getElementById('agent-upload-content');
                        if (uploadArea && uploadContent) {{
                            uploadContent.innerHTML = `
                                <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                                    <span class="material-symbols-outlined" style="font-size: 1.2rem;">check_circle</span>
                                    <div style="text-align: left;">
                                        <div style="font-weight: 600; font-size: 0.8rem; color: var(--gray-700);">Ready for Analysis</div>
                                        <div style="font-size: 0.7rem; color: var(--gray-500); margin-top: 0.1rem;">{e.name}</div>
                                    </div>
                                    <button onclick="event.stopPropagation(); resetAgentUpload()" class="upload-delete-btn">×</button>
                                </div>
                            `;
                        }}
                    ''')

                    # Add user message
                    add_message_to_chat(messages_container, 'user', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">description</span> Uploaded: {e.name}')

                    # Start intelligent data analysis and parameter recommendation
                    add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">search</span> **Data Analysis Initiated!** I\'m examining your dataset structure and preparing optimal analysis parameters for you...')

                    # Send initial analysis request to trigger backend workflow
                    ui.timer(2.0, lambda: send_initial_analysis_request(messages_container, file_id), once=True)

                    # Update data preview in left panel (if function exists)
                    try:
                        update_data_preview(content, e.name)
                    except Exception as preview_error:
                        print(f"Preview update error: {preview_error}")

                    # Store file_id in global state and reset conversation history
                    global current_agent_file_id, agent_conversation_history
                    current_agent_file_id = file_id
                    agent_conversation_history = []  # Reset conversation history for new file

                    # Store file_id in JavaScript global for reset function
                    ui.run_javascript(f'window.currentAgentFileId = "{file_id}";')

                    ui.run_javascript('document.querySelector(".chat-messages").scrollTop = document.querySelector(".chat-messages").scrollHeight;')
                else:
                    error_text = await resp.text()
                    if resp.status == 413:
                        error_msg = "File is too large for the server to process."
                    elif resp.status == 415:
                        error_msg = "File type not supported. Please ensure it's a valid CSV file."
                    else:
                        error_msg = f"Upload failed (HTTP {resp.status})"

                    add_message_to_chat(messages_container, 'assistant', f'❌ {error_msg}: {error_text}')
                    # Reset upload area on error
                    ui.run_javascript('resetAgentUpload();')

    except asyncio.TimeoutError:
        add_message_to_chat(messages_container, 'assistant', '⏰ Upload timed out. Please try again with a smaller file or check your connection.')
        ui.run_javascript('resetAgentUpload();')

    except Exception as ex:
        error_msg = str(ex)
        if "connection" in error_msg.lower():
            add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">language</span> Upload failed due to connection issues. Please check your internet connection and try again.')
        else:
            add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Upload error: {error_msg}')

        # Reset upload area on error
        ui.run_javascript('resetAgentUpload();')

def update_data_preview(content, filename):
    """Update the data preview in the left panel"""
    try:
        # Parse CSV content
        import io
        import csv

        # Convert bytes to string if needed
        if isinstance(content, bytes):
            content_str = content.decode('utf-8')
        else:
            content_str = str(content)

        # Parse CSV
        csv_reader = csv.reader(io.StringIO(content_str))
        rows = list(csv_reader)

        if not rows:
            preview_html = '''
                <div style="text-align: center; color: var(--error-600); padding: 2rem;">
                    <span class="material-symbols-outlined" style="font-size: 2rem; margin-bottom: 1rem; display: block;">cancel</span>
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">Empty File</div>
                    <div style="font-size: 0.9rem;">The uploaded file appears to be empty</div>
                </div>
            '''
        else:
            # Get header and all rows for full data preview with scrolling
            headers = rows[0] if rows else []
            data_rows = rows[1:]  # Show all data rows for scrolling functionality

            # Build compact preview table with file info at top
            table_html = f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; font-size: 0.85rem;">'
            table_html += f'<div style="font-weight: 600; color: #011f5b;"><span class="material-symbols-outlined" style="font-size: 1rem; margin-right: 0.25rem; vertical-align: middle; color: #011f5b;">analytics</span> {filename}</div>'
            table_html += f'<div style="color: var(--gray-600);">{len(rows)-1} rows × {len(headers)} cols</div>'
            table_html += '</div>'

            # More compact table styling with horizontal scroll support
            table_html += '<div style="overflow-x: auto; max-width: 100%; border-radius: 8px; overflow: hidden;"><table style="width: 100%; border-collapse: collapse; font-size: 0.75rem; line-height: 1.2; min-width: max-content; table-layout: auto;">'
            # Header row - show all columns with horizontal scrolling
            table_html += '<thead><tr style="background: #011f5b;">'
            for header in headers:  # Show all columns with horizontal scrolling
                table_html += f'<th style="padding: 0.4rem 0.3rem; text-align: left; border: 1px solid var(--gray-200); font-weight: 600; color: white; min-width: 80px; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{header}</th>'
            table_html += '</tr></thead>'

            # Data rows - show all columns with horizontal scrolling
            table_html += '<tbody>'
            for row in data_rows:
                table_html += '<tr style="background: white;">'
                for cell in row:  # Show all columns with horizontal scrolling
                    table_html += f'<td style="padding: 0.4rem 0.3rem; border: 1px solid var(--gray-200); min-width: 80px; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{cell}</td>'
                table_html += '</tr>'
            table_html += '</tbody></table></div>'

            # Show row count info at bottom
            if len(data_rows) < len(rows) - 1:
                table_html += f'<div style="margin-top: 0.5rem; font-size: 0.7rem; color: var(--gray-500); text-align: center;">Showing {len(data_rows)} rows of {len(rows)-1} total rows</div>'
            else:
                table_html += f'<div style="margin-top: 0.5rem; font-size: 0.7rem; color: var(--gray-500); text-align: center;">{len(rows)-1} rows total</div>'

            preview_html = table_html

    except Exception as ex:
        preview_html = f'''
            <div style="text-align: center; color: var(--error-600); padding: 2rem;">
                <span class="material-symbols-outlined" style="font-size: 2rem; margin-bottom: 1rem; display: block;">warning</span>
                <div style="font-weight: 600; margin-bottom: 0.5rem;">Preview Error</div>
                <div style="font-size: 0.9rem;">Unable to preview file: {str(ex)}</div>
            </div>
        '''

    # Update the data preview container
    ui.run_javascript(f'''
        const previewContainer = document.querySelector('.data-preview-container');
        if (previewContainer) {{
            previewContainer.innerHTML = `{preview_html}`;
        }}
    ''')

def add_message_to_chat(messages_container, role, content):
    """Add a message to the chat container and conversation history"""
    global agent_conversation_history

    # Add to conversation history
    agent_conversation_history.append({
        'role': role,
        'content': content
    })

    # Keep only last 50 messages to avoid memory issues
    if len(agent_conversation_history) > 50:
        agent_conversation_history = agent_conversation_history[-50:]

    with messages_container:
        with ui.element('div').classes(f'message {role}').style('''
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1rem;
            align-items: flex-start;
        '''):
            if role == 'assistant':
                ui.html('<div class="message-avatar" style="background: #011f5b; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0;"><span class="material-symbols-outlined" style="font-size: 1.2rem;">support_agent</span></div>')
                sender = 'AI Assistant'
                avatar_bg = 'var(--primary-600)'
            else:
                ui.html('<div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0;"><span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">person</span></div>')
                sender = 'You'
                avatar_bg = '#011f5b'

            with ui.element('div').classes('message-content').style('flex: 1;'):
                ui.html(f'<div class="message-sender" style="font-weight: 600; color: {avatar_bg}; font-size: 0.85rem; margin-bottom: 0.25rem;">{sender}</div>')
                ui.html(f'<div class="message-text" style="background: white; padding: 0.75rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200); font-size: 0.9rem; line-height: 1.5; white-space: pre-wrap;">{content}</div>')

async def send_agent_message(input_field, messages_container, status_area):
    """Enhanced agent message sending with intelligent context management and user guidance"""
    message = input_field.value.strip()
    if not message:
        return

    # Validate input based on current workflow stage
    current_stage = get_current_workflow_stage()
    validation = validate_user_input(message, current_stage)

    if not validation["valid"]:
        add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> {validation["reason"]}')
        return

    # Update context with user activity
    update_agent_context()

    # Check if file is uploaded before allowing complex operations
    global current_agent_file_id
    if not current_agent_file_id and any(keyword in message.lower() for keyword in ['analyze', 'run', 'process', 'start']):
        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">upload_file</span> Please upload a CSV file first before requesting analysis.')
        return

    # Clear input
    input_field.value = ''

    # Add user message
    add_message_to_chat(messages_container, 'user', message)

    # Show typing indicator with enhanced styling
    typing_indicator = None
    with messages_container:
        typing_indicator = ui.element('div').classes('message assistant').style('''
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1rem;
            align-items: flex-start;
        ''')
        with typing_indicator:
            ui.html('<div class="message-avatar" style="background: #011f5b; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0;"><span class="material-symbols-outlined" style="font-size: 1.2rem;">support_agent</span></div>')
            with ui.element('div').classes('message-content').style('flex: 1;'):
                ui.html('<div class="message-text" style="background: white; padding: 0.75rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200); font-size: 0.9rem;"><em>Analyzing your request...</em></div>')

    ui.run_javascript('document.querySelector(".chat-messages").scrollTop = document.querySelector(".chat-messages").scrollHeight;')

    try:
        # Prepare messages for API with enhanced context
        messages = []

        # Add recent conversation history for context (last 10 messages)
        recent_history = agent_conversation_history[-10:] if agent_conversation_history else []
        for msg in recent_history:
            if msg['role'] != 'system':  # Skip system messages in history
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

        # Add context about uploaded file if available
        if current_agent_file_id:
            messages.append({
                'role': 'system',
                'content': f'User has uploaded a file with ID: {current_agent_file_id}. Continue ranking analysis workflow.'
            })

        # Add enhanced workflow stage context
        workflow_stage = get_current_workflow_stage()
        guidance = get_workflow_guidance(workflow_stage)

        context_message = f'''Current workflow stage: {workflow_stage}.
        User context: {agent_context['data_insights'] if agent_context['data_insights'] else 'No data insights yet'}.
        Guide user through: {', '.join(guidance['next_steps'])}.
        Tips: {guidance['tips']}'''

        messages.append({
            'role': 'system',
            'content': context_message
        })

        # Add the current user message
        messages.append({
            'role': 'user',
            'content': message
        })

        # Call agent chat API with timeout
        async with aiohttp.ClientSession() as session:
            payload = {'messages': messages}
            async with session.post(f'{API_BASE_URL}/api/agent/chat', json=payload, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()

                    # Remove typing indicator
                    if typing_indicator:
                        typing_indicator.clear()

                    # Process response with enhanced error handling
                    if result.get('error'):
                        error_msg = result["error"]
                        if "timeout" in error_msg.lower():
                            add_message_to_chat(messages_container, 'assistant', '⏰ Request timed out. Please try again or use a smaller dataset.')
                        elif "file" in error_msg.lower():
                            add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">description</span> File issue: {error_msg}. Please check your CSV file and try again.')
                        else:
                            add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Error: {error_msg}')
                    else:
                        # Get the last assistant message
                        assistant_message = result.get('assistant_message', {})
                        content = assistant_message.get('content', '')

                        if content:
                            # Check if this is a workflow guidance message
                            if any(phrase in content.lower() for phrase in ['next step', 'would you like', 'please confirm']):
                                add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">description</span> {content}')
                            else:
                                add_message_to_chat(messages_container, 'assistant', content)

                        # Check for tool calls and display results with enhanced feedback
                        tool_calls = assistant_message.get('tool_calls', [])
                        if tool_calls:
                            for tool_call in tool_calls:
                                func = tool_call.get('function', {})
                                tool_name = func.get('name', 'Unknown Tool')

                                # Provide user-friendly tool descriptions
                                tool_descriptions = {
                                    'inspect_dataset': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">search</span> Analyzing your dataset structure...',
                                    'infer_direction': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">compass_calibration</span> Determining ranking direction...',
                                    'estimate_runtime': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">schedule</span> Estimating analysis time...',
                                    'create_job': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">rocket_launch</span> Starting analysis job...',
                                    'poll_status': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">analytics</span> Checking progress...',
                                    'get_results': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">bar_chart</span> Retrieving results...'
                                }

                                friendly_msg = tool_descriptions.get(tool_name, f'<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">build</span> Executing: {tool_name}...')
                                add_message_to_chat(messages_container, 'assistant', friendly_msg)

                        # Check if we should display analysis results
                        for tool_call in tool_calls:
                            func = tool_call.get('function', {})
                            if func.get('name') == 'create_job':
                                # Extract job_id from tool arguments
                                args = func.get('arguments', {})
                                if isinstance(args, str):
                                    try:
                                        import json
                                        args = json.loads(args)
                                    except:
                                        continue

                                # The job_id is actually the file_id in this context
                                file_id = args.get('file_id')
                                if file_id:
                                    global current_agent_job_id
                                    current_agent_job_id = file_id
                                    # Poll for results and display report
                                    ui.timer(2.0, lambda: check_agent_job_status(messages_container, file_id), once=True)

                else:
                    # Remove typing indicator
                    if typing_indicator:
                        typing_indicator.clear()

                    if resp.status == 429:
                        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">bolt</span> Too many requests. Please wait a moment before trying again.')
                    elif resp.status >= 500:
                        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">build</span> Server error. Please try again in a few moments.')
                    else:
                        error_text = await resp.text()
                        add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> API Error: {resp.status} - {error_text}')

    except asyncio.TimeoutError:
        # Remove typing indicator
        if typing_indicator:
            typing_indicator.remove()
        add_message_to_chat(messages_container, 'assistant', '⏰ Request timed out. Please try again or check your connection.')

    except Exception as ex:
        # Remove typing indicator
        if typing_indicator:
            typing_indicator.remove()

        error_msg = str(ex)
        if "connection" in error_msg.lower():
            add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">language</span> Connection error. Please check your internet connection and try again.')
        else:
            add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Unexpected error: {error_msg}')

    # Scroll to bottom
    ui.run_javascript('document.querySelector(".chat-messages").scrollTop = document.querySelector(".chat-messages").scrollHeight;')

    # Update suggestions area after sending message
    current_stage = get_current_workflow_stage()
    update_suggestions_area(suggestions_area, current_stage, agent_context, messages_container, input_field)


def get_current_workflow_stage():
    """Determine current workflow stage based on agent state"""
    global current_agent_file_id, current_agent_job_id
    if not current_agent_file_id:
        return "awaiting_upload"
    elif not current_agent_job_id:
        return "data_analysis"
    else:
        return "analysis_running"


# Enhanced context and progress tracking
agent_context = {
    'conversation_history': [],
    'current_stage': 'awaiting_upload',
    'user_preferences': {},
    'data_insights': {},
    'last_activity': None
}


def update_agent_context(stage=None, data=None, preferences=None):
    """Update agent context and track progress"""
    global agent_context

    if stage:
        agent_context['current_stage'] = stage

    if data:
        agent_context['data_insights'].update(data)

    if preferences:
        agent_context['user_preferences'].update(preferences)

    agent_context['last_activity'] = asyncio.get_event_loop().time()

    # Store conversation history (keep last 20 exchanges)
    agent_context['conversation_history'].append({
        'timestamp': agent_context['last_activity'],
        'stage': agent_context['current_stage'],
        'type': 'context_update'
    })

    if len(agent_context['conversation_history']) > 20:
        agent_context['conversation_history'] = agent_context['conversation_history'][-20:]


def get_workflow_guidance(stage):
    """Provide stage-specific guidance and next steps"""
    guidance = {
        'awaiting_upload': {
            'welcome': '👋 Welcome! Please upload your CSV file to begin the ranking analysis.',
            'next_steps': ['Upload CSV file', 'Review data structure', 'Configure analysis parameters'],
            'tips': 'Ensure your CSV contains performance metrics columns for best results.'
        },
        'data_analysis': {
            'welcome': '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">analytics</span> Great! I\'ve analyzed your data. Let\'s configure the analysis.',
            'next_steps': ['Review data insights', 'Set ranking direction', 'Choose parameters', 'Start analysis'],
            'tips': 'I can help you understand your data structure and recommend optimal settings.'
        },
        'analysis_running': {
            'welcome': '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">rocket_launch</span> Analysis is running! I\'ll notify you when results are ready.',
            'next_steps': ['Monitor progress', 'View results when complete'],
            'tips': 'The analysis time depends on your dataset size and parameters chosen.'
        }
    }

    return guidance.get(stage, guidance['awaiting_upload'])


def validate_user_input(input_text, current_stage):
    """Validate user input based on current workflow stage"""
    if not input_text or not input_text.strip():
        return {"valid": False, "reason": "Please provide a message."}

    input_lower = input_text.lower().strip()

    # Stage-specific validations
    if current_stage == 'awaiting_upload':
        if any(keyword in input_lower for keyword in ['analyze', 'run', 'process', 'start']):
            return {"valid": False, "reason": "Please upload a CSV file first before requesting analysis."}

    elif current_stage == 'data_analysis':
        # Allow analysis-related queries and direction choices
        valid_keywords = ['analyze', 'run', 'process', 'parameter', 'setting', 'direction', 'column', 'data', 'higher', 'lower', 'yes', 'confirm', 'proceed']
        if not any(keyword in input_lower for keyword in valid_keywords):
            return {"valid": False, "reason": "Please ask about data analysis, parameters, or request to start the analysis."}

    return {"valid": True}


def get_intelligent_suggestions(current_stage, context):
    """Provide intelligent suggestions based on current stage and context"""
    suggestions = []

    if current_stage == 'awaiting_upload':
        suggestions = [
            "Upload your CSV file to get started",
            "Ask me about supported data formats",
            "Learn about ranking analysis capabilities"
        ]

    elif current_stage == 'data_analysis':
        data_insights = context.get('data_insights', {})

        if data_insights.get('numeric_candidates'):
            suggestions.append(f"Review the {len(data_insights['numeric_candidates'])} numeric columns I found")

        if not context.get('direction_confirmed'):
            suggestions.append("Confirm the ranking direction (higher/lower is better)")

        suggestions.extend([
            "Ask me to recommend optimal parameters",
            "Start the analysis with current settings",
            "Learn more about bootstrap iterations"
        ])

    elif current_stage == 'analysis_running':
        suggestions = [
            "Check analysis progress",
            "Learn about what happens during analysis",
            "Prepare questions for when results are ready"
        ]

    return suggestions[:3]  # Return top 3 suggestions


async def send_initial_analysis_request(messages_container, file_id):
    """Send initial analysis request to trigger backend workflow"""
    print(f"DEBUG: Sending analysis request for file_id: {file_id}")
    try:
        # Send a message that will trigger the backend's intelligent analysis workflow
        analysis_message = f"START ANALYSIS - I have uploaded a CSV file with ID: {file_id}. Please immediately use the inspect_dataset tool to analyze the data structure, then infer_direction to determine ranking direction, and estimate_runtime to provide time estimates."

        # Prepare messages for API
        messages = [
            {'role': 'system', 'content': f'User has uploaded a file with ID: {file_id}. This is a START ANALYSIS request - immediately execute: inspect_dataset → infer_direction → estimate_runtime workflow.'},
            {'role': 'user', 'content': analysis_message}
        ]

        async with aiohttp.ClientSession() as session:
            payload = {'messages': messages}
            try:
                async with session.post(f'{API_BASE_URL}/api/agent/chat', json=payload, timeout=60) as resp:
                    if resp.status == 200:
                        result = await resp.json()

                        # Process and display the response
                        if result.get('assistant_message'):
                            content = result['assistant_message'].get('content', '')
                            if content:
                                add_message_to_chat(messages_container, 'assistant', content)

                            # Handle tool calls if present
                            tool_calls = result['assistant_message'].get('tool_calls', [])
                            if tool_calls:
                                for tool_call in tool_calls:
                                    func = tool_call.get('function', {})
                                    tool_name = func.get('name', 'Unknown Tool')
                                    add_message_to_chat(messages_container, 'assistant', f'🔧 Executing: {tool_name}...')

                        elif result.get('error'):
                            add_message_to_chat(messages_container, 'assistant', f'❌ Backend error: {result["error"]}')
                        else:
                            add_message_to_chat(messages_container, 'assistant', '❌ No response from analysis. Please try again.')

                    else:
                        error_text = await resp.text()
                        add_message_to_chat(messages_container, 'assistant', f'❌ Server error ({resp.status}): {error_text}')

            except asyncio.TimeoutError:
                add_message_to_chat(messages_container, 'assistant', '⏰ Analysis request timed out. The server may be busy or the API key may be invalid.')
            except Exception as e:
                add_message_to_chat(messages_container, 'assistant', f'❌ Network error: {str(e)}. Please check your connection.')

    except Exception as ex:
        add_message_to_chat(messages_container, 'assistant', f'❌ Analysis request failed: {str(ex)}')

    # Update context
    update_agent_context(stage='data_analysis', data={'file_analyzed': True})


def update_suggestions_area(suggestions_area, current_stage, context, messages_container=None, input_field=None):
    """Update the suggestions area with current intelligent suggestions"""
    suggestions = get_intelligent_suggestions(current_stage, context)

    # Clear existing suggestions
    suggestions_area.clear()

    with suggestions_area:
        if suggestions:
            ui.html('<div style="font-size: 0.8rem; color: var(--gray-600); margin-bottom: 0.5rem; font-weight: 600;">💡 Suggested next steps:</div>')
            with ui.element('div').style('display: flex; flex-wrap: wrap; gap: 0.5rem;'):
                for suggestion in suggestions:
                    ui.button(
                        suggestion,
                        on_click=lambda s=suggestion: handle_suggestion_click(s, input_field, messages_container, status_area) if input_field and messages_container and status_area else [
                            # Find input field and set value
                            input_field.run_method('focus') if input_field else None,
                            # This would need to be implemented to set the input value
                            # For now, we'll just add the suggestion as a message
                            add_message_to_chat(messages_container, 'user', s) if messages_container else None
                        ]
                    ).props('flat dense size=sm').style('font-size: 0.75rem; padding: 0.25rem 0.5rem;')
        else:
            ui.html('<div style="font-size: 0.8rem; color: var(--gray-500); text-align: center;">No suggestions available</div>')

def handle_suggestion_click(suggestion, input_field, messages_container, status_area):
    """Handle clicks on suggestion buttons with special logic for certain suggestions"""
    if suggestion == "Start the analysis with current settings":
        # Directly trigger analysis like manual mode - bypass Agent conversation
        message = "Please start the analysis with the current settings and parameters."

        # Check if file is uploaded
        global current_agent_file_id
        if not current_agent_file_id:
            add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">upload_file</span> Please upload a CSV file first before requesting analysis.')
            return

        # Clear input
        input_field.value = ''

        # Add user message
        add_message_to_chat(messages_container, 'user', message)

        # Directly start analysis like manual mode
        ui.timer(0.1, lambda: asyncio.create_task(direct_agent_analysis(current_agent_file_id, messages_container)), once=True)
    else:
        # For other suggestions, just add to chat and focus input
        add_message_to_chat(messages_container, 'user', suggestion)
        input_field.run_method('focus')

async def direct_agent_analysis(file_id: str, messages_container):
    """Direct analysis for Agent mode - bypass conversation and generate report immediately"""
    try:
        # Clear previous content and show enhanced loading status
        if report_container_ref is None or status_container_ref is None:
            add_message_to_chat(messages_container, 'assistant', '❌ Report system not ready. Please refresh the page.')
            return

        report_container_ref.clear()
        status_container_ref.clear()
        # Make containers visible
        status_container_ref.style('display: block;')
        report_container_ref.style('display: none;')

        # Enhanced loading animation
        with status_container_ref:
            with ui.element('div').classes('status-card').style('''
                background: linear-gradient(135deg, rgba(1, 31, 91, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%);
                border: 1px solid rgba(1, 31, 91, 0.1);
                backdrop-filter: blur(15px);
            '''):
                ui.html('''
                    <div style="display: flex; align-items: center; gap: 1.5rem; justify-content: center;">
                        <div class="loading-spinner"></div>
                        <div style="color: var(--primary-900); font-weight: 700; font-size: 1.1rem;">
                            🔍 Performing robust ranking analysis...
                        </div>
                    </div>
                    <div style="margin-top: 1rem; text-align: center; color: var(--gray-600); font-size: 0.9rem;">
                        Please wait while we process your report
                    </div>
                ''')

        # Get file content from agent backend
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/api/agent/files/{file_id}', timeout=30) as resp:
                if resp.status != 200:
                    status_container_ref.clear()
                    with status_container_ref:
                        with ui.element('div').classes('status-card info-card error').style('''
                            background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
                            border-left: 5px solid var(--error-500);
                        '''):
                            ui.html('''
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <div style="font-size: 1.5rem;">❌</div>
                                    <div>
                                        <div style="color: var(--error-600); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
                                            File Access Failed
                                        </div>
                                        <div style="color: var(--gray-700); font-size: 0.95rem;">
                                            Could not access uploaded file. Please try uploading again.
                                        </div>
                                    </div>
                                </div>
                            ''')
                    return

                file_bytes = await resp.read()

        # Use default parameters for Agent mode
        bigbetter = True  # higher is better by default
        B = 2000  # bootstrap samples
        seed = 1

        # Create job
        file_name = 'agent_data.csv'
        job_id, err = await create_job_async(file_name, file_bytes, bigbetter, B, seed)
        if err or not job_id:
            logger.error(f"Create job failed: {err}")
            status_container_ref.clear()
            with status_container_ref:
                with ui.element('div').classes('status-card info-card error').style('''
                    background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
                    border-left: 5px solid var(--error-500);
                '''):
                    ui.html(f'''
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div style="font-size: 1.5rem;">❌</div>
                            <div>
                                <div style="color: var(--error-600); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
                                    Analysis Failed
                                </div>
                                <div style="color: var(--gray-700); font-size: 0.95rem;">
                                    {err or 'Job creation failed'}
                                </div>
                            </div>
                        </div>
                    ''')
            return

        # Poll status
        status = await poll_status_async(job_id)
        if status.get('status') != 'succeeded':
            status_container_ref.clear()
            with status_container_ref:
                with ui.element('div').classes('status-card info-card error').style('''
                    background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
                    border-left: 5px solid var(--error-500);
                '''):
                    ui.html(f'''
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div style="font-size: 1.5rem;">❌</div>
                            <div>
                                <div style="color: var(--error-600); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
                                    Analysis Failed
                                </div>
                                <div style="color: var(--gray-700); font-size: 0.95rem;">
                                    {status.get("message","Unknown error")}
                                </div>
                            </div>
                        </div>
                    ''')
            return

        # Fetch results
        result, err = await fetch_results_async(job_id)
        if err or not result:
            status_container_ref.clear()
            with status_container_ref:
                with ui.element('div').classes('status-card info-card error').style('''
                    background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
                    border-left: 5px solid var(--error-500);
                '''):
                    ui.html(f'''
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div style="font-size: 1.5rem;">❌</div>
                            <div>
                                <div style="color: var(--error-600); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
                                    Results Fetch Failed
                                </div>
                                <div style="color: var(--gray-700); font-size: 0.95rem;">
                                    {err or 'Could not retrieve results'}
                                </div>
                            </div>
                        </div>
                    ''')
            return

        # Clear status and show results
        status_container_ref.clear()
        status_container_ref.style('display: none;')
        report_container_ref.style('display: block;')

        # Add success message to chat
        add_message_to_chat(messages_container, 'assistant', '✅ **Analysis Complete!** Your spectral ranking analysis has finished successfully. Displaying the complete analysis report below.')

        with report_container_ref:
            show_results(result)

        # Scroll to the report
        ui.run_javascript('document.querySelector("#results").scrollIntoView({behavior: "smooth"});')

    except Exception as e:
        print(f"Error in direct agent analysis: {e}")
        try:
            if status_container_ref:
                status_container_ref.clear()
                with status_container_ref:
                    with ui.element('div').classes('status-card info-card error').style('''
                        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
                        border-left: 5px solid var(--error-500);
                    '''):
                        ui.html(f'''
                            <div style="display: flex; align-items: center; gap: 1rem;">
                                <div style="font-size: 1.5rem;">❌</div>
                                <div>
                                    <div style="color: var(--error-600); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
                                        Unexpected Error
                                    </div>
                                    <div style="color: var(--gray-700); font-size: 0.95rem;">
                                        {str(e)}
                                    </div>
                                </div>
                            </div>
                        ''')
        except:
            add_message_to_chat(messages_container, 'assistant', f'❌ Unexpected error: {str(e)}')

async def process_agent_analysis_async(message, messages_container, typing_indicator, input_field=None):
    """Process the agent analysis request asynchronously"""
    global _analysis_completed
    try:
        # Prepare messages for API with enhanced context
        messages = []

        # Add recent conversation history for context (last 10 messages)
        recent_history = agent_conversation_history[-10:] if agent_conversation_history else []
        for msg in recent_history:
            if msg['role'] != 'system':  # Skip system messages in history
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

        # Add context about uploaded file if available
        if current_agent_file_id:
            messages.append({
                'role': 'system',
                'content': f'User has uploaded a file with ID: {current_agent_file_id}. Continue ranking analysis workflow.'
            })

        # Add enhanced workflow stage context
        workflow_stage = get_current_workflow_stage()
        guidance = get_workflow_guidance(workflow_stage)

        context_message = f'''Current workflow stage: {workflow_stage}.
        User context: {agent_context['data_insights'] if agent_context['data_insights'] else 'No data insights yet'}.
        Guide user through: {', '.join(guidance['next_steps'])}.
        Tips: {guidance['tips']}'''

        messages.append({
            'role': 'system',
            'content': context_message
        })

        # Add the current user message
        messages.append({
            'role': 'user',
            'content': message
        })

        # Call agent chat API with timeout
        async with aiohttp.ClientSession() as session:
            payload = {'messages': messages}
            async with session.post(f'{API_BASE_URL}/api/agent/chat', json=payload, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()

                    # Remove typing indicator
                    if typing_indicator:
                        typing_indicator.clear()

                    # Process response with enhanced error handling
                    if result.get('error'):
                        error_msg = result["error"]
                        if "timeout" in error_msg.lower():
                            add_message_to_chat(messages_container, 'assistant', '⏰ Request timed out. Please try again or use a smaller dataset.')
                        elif "file" in error_msg.lower():
                            add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">description</span> File issue: {error_msg}. Please check your CSV file and try again.')
                        else:
                            add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Error: {error_msg}')
                    else:
                        # Get the last assistant message
                        assistant_message = result.get('assistant_message', {})
                        content = assistant_message.get('content', '')

                        if content:
                            # Check if this is a workflow guidance message
                            if any(phrase in content.lower() for phrase in ['next step', 'would you like', 'please confirm']):
                                add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">description</span> {content}')
                            else:
                                add_message_to_chat(messages_container, 'assistant', content)

                        # Check for tool calls and display results with enhanced feedback
                        tool_calls = assistant_message.get('tool_calls', [])
                        if tool_calls:
                            for tool_call in tool_calls:
                                func = tool_call.get('function', {})
                                tool_name = func.get('name', 'Unknown Tool')

                                # Provide user-friendly tool descriptions
                                tool_descriptions = {
                                    'inspect_dataset': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">search</span> Analyzing your dataset structure...',
                                    'infer_direction': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">compass_calibration</span> Determining ranking direction...',
                                    'estimate_runtime': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">schedule</span> Estimating analysis time...',
                                    'create_job': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">rocket_launch</span> Starting analysis job...',
                                    'poll_status': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">analytics</span> Checking progress...',
                                    'get_results': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">bar_chart</span> Retrieving results...'
                                }

                                friendly_msg = tool_descriptions.get(tool_name, f'<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">build</span> Executing: {tool_name}...')
                                add_message_to_chat(messages_container, 'assistant', friendly_msg)

                        # Check if we should display analysis results
                        for tool_call in tool_calls:
                            func = tool_call.get('function', {})
                            if func.get('name') == 'create_job':
                                # Extract job_id from tool arguments
                                args = func.get('arguments', {})
                                if isinstance(args, str):
                                    try:
                                        import json
                                        args = json.loads(args)
                                    except:
                                        continue

                                # The job_id is actually the file_id in this context
                                file_id = args.get('file_id')
                                if file_id:
                                    global current_agent_job_id
                                    current_agent_job_id = file_id
                                    # Poll for results and display report
                                    ui.timer(2.0, lambda: check_agent_job_status(messages_container, file_id), once=True)

                else:
                    # Remove typing indicator
                    if typing_indicator:
                        typing_indicator.clear()

                    if resp.status == 429:
                        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">bolt</span> Too many requests. Please wait a moment before trying again.')
                    elif resp.status >= 500:
                        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">build</span> Server error. Please try again in a few moments.')
                    else:
                        error_text = await resp.text()
                        add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> API Error: {resp.status} - {error_text}')

    except asyncio.TimeoutError:
        # Remove typing indicator
        if typing_indicator:
            typing_indicator.clear()
        add_message_to_chat(messages_container, 'assistant', '⏰ Request timed out. Please try again or check your connection.')

    except Exception as ex:
        # Remove typing indicator
        if typing_indicator:
            typing_indicator.clear()

        error_msg = str(ex)
        if "connection" in error_msg.lower():
            add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">language</span> Connection error. Please check your internet connection and try again.')
        else:
            add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Unexpected error: {error_msg}')

    # Set completion flag to trigger UI updates in main thread
    _analysis_completed = True
    return True

# Global variables to store agent state
current_agent_file_id = None
current_agent_job_id = None
_analysis_completed = False

# Agent conversation history for context
agent_conversation_history = []

def reset_agent_upload_state():
    """Reset the agent upload state"""
    global current_agent_file_id, agent_conversation_history
    current_agent_file_id = None
    agent_conversation_history = []

def reset_manual_upload_state():
    """Reset the manual upload state"""
    # This function will be called from JavaScript to reset Python state
    pass

async def check_agent_job_status(messages_container, job_id):
    """Enhanced job status checking with better progress feedback"""
    try:
        async with aiohttp.ClientSession() as session:
            # Check status
            async with session.get(f'{API_BASE_URL}/api/ranking/jobs/{job_id}/status', timeout=30) as resp:
                if resp.status == 200:
                    status_data = await resp.json()
                    status = status_data.get('status', 'unknown')
                    user_message = status_data.get('status_message', '')

                    if status == 'succeeded':
                        # Show progress message
                        add_message_to_chat(messages_container, 'assistant', '📊 Analysis completed! Retrieving results...')

                        # Get results with retry logic
                        max_retries = 3
                        for attempt in range(max_retries):
                            async with session.get(f'{API_BASE_URL}/api/ranking/jobs/{job_id}/results', timeout=60) as results_resp:
                                if results_resp.status == 200:
                                    results = await results_resp.json()

                                    # Add success message with summary
                                    summary_msg = '✅ **Analysis Complete!** Your spectral ranking analysis has finished successfully. '
                                    if 'methods' in results:
                                        num_rankings = len(results.get('methods', []))
                                        summary_msg += f'Generated {num_rankings} ranking results. '

                                    summary_msg += 'Displaying the complete analysis report now.'
                                    add_message_to_chat(messages_container, 'assistant', summary_msg)

                                    # Scroll to bottom
                                    ui.run_javascript('document.querySelector(".chat-messages").scrollTop = document.querySelector(".chat-messages").scrollHeight;')

                                    # Show report using the same mechanism as manual mode
                                    ui.timer(1.0, lambda: show_main_report(results), once=True)
                                    break

                                elif results_resp.status == 404:
                                    if attempt < max_retries - 1:
                                        # Wait and retry
                                        await asyncio.sleep(2)
                                        continue
                                    else:
                                        add_message_to_chat(messages_container, 'assistant', '❌ Results not found. The analysis may have been deleted.')
                                        break

                                else:
                                    if attempt < max_retries - 1:
                                        await asyncio.sleep(1)
                                        continue
                                    else:
                                        add_message_to_chat(messages_container, 'assistant', f'❌ Failed to retrieve results after {max_retries} attempts.')
                                        break

                    elif status == 'failed':
                        error_msg = status_data.get("message", "Unknown error")
                        if "timeout" in error_msg.lower():
                            add_message_to_chat(messages_container, 'assistant', '⏰ Analysis timed out. Please try again with different parameters or a smaller dataset.')
                        elif "memory" in error_msg.lower():
                            add_message_to_chat(messages_container, 'assistant', '💾 Analysis failed due to memory constraints. Please try with a smaller dataset or fewer bootstrap iterations.')
                        else:
                            add_message_to_chat(messages_container, 'assistant', f'❌ Analysis failed: {error_msg}')

                    elif status == 'running':
                        # Show progress with encouraging message
                        progress_msg = user_message or '🔄 Analysis is still running...'
                        if 'progress' in status_data:
                            progress = status_data.get('progress', 0)
                            progress_msg = f'🔄 Analysis in progress ({progress}% complete)...'

                        add_message_to_chat(messages_container, 'assistant', progress_msg)
                        # Check again in a shorter interval for running jobs
                        ui.timer(2.0, lambda: check_agent_job_status(messages_container, job_id), once=True)

                    else:
                        add_message_to_chat(messages_container, 'assistant', f'⚠️ Unknown job status: {status}')

                elif resp.status == 404:
                    add_message_to_chat(messages_container, 'assistant', '❌ Job not found. The analysis may have expired or been deleted.')
                elif resp.status == 429:
                    add_message_to_chat(messages_container, 'assistant', '⚡ Server is busy. Retrying in a moment...')
                    ui.timer(5.0, lambda: check_agent_job_status(messages_container, job_id), once=True)
                else:
                    add_message_to_chat(messages_container, 'assistant', f'❌ Status check failed (HTTP {resp.status}). Retrying...')

                    # Retry on other errors
                    ui.timer(3.0, lambda: check_agent_job_status(messages_container, job_id), once=True)

    except asyncio.TimeoutError:
        add_message_to_chat(messages_container, 'assistant', '⏰ Status check timed out. Retrying...')
        ui.timer(3.0, lambda: check_agent_job_status(messages_container, job_id), once=True)

    except Exception as ex:
        error_msg = str(ex)
        if "connection" in error_msg.lower():
            add_message_to_chat(messages_container, 'assistant', '🌐 Connection error while checking status. Retrying...')
        else:
            add_message_to_chat(messages_container, 'assistant', f'❌ Error checking job status: {error_msg}. Retrying...')

        # Retry on errors
        ui.timer(3.0, lambda: check_agent_job_status(messages_container, job_id), once=True)

def show_main_report(result):
    """Display analysis report in the main report container (used by both agent and manual modes)."""
    try:
        # Check if report container is initialized
        if report_container_ref is None or status_container_ref is None:
            print(f"Report containers not initialized yet. report_container_ref: {report_container_ref}, status_container_ref: {status_container_ref}")
            # Retry after a short delay
            ui.timer(0.5, lambda: show_main_report(result), once=True)
            return

        # Clear previous content and show the report in main container
        report_container_ref.clear()
        status_container_ref.clear()

        # Make containers visible
        status_container_ref.style('display: none;')
        report_container_ref.style('display: block;')

        with report_container_ref:
            show_results(result)

        # Scroll to the report
        ui.run_javascript('document.querySelector("#results").scrollIntoView({behavior: "smooth"});')

    except Exception as e:
        print(f"Error displaying main report: {e}")
        ui.notify(f'Error displaying report: {str(e)}', type='negative')

def show_report(report):
    with ui.element('div').classes('report-card').style('max-width: 1400px; margin: 0 auto; width: 100%;'):
        # Enhanced Report Header with Card Structure
        with ui.element('div').classes('report-header'):
            with ui.element('div').classes('card-header').style('justify-content: center; flex-direction: column; text-align: center; margin-bottom: 2rem;'):
                with ui.element('div').classes('card-icon-container').style('margin: 0 auto 1rem; width: 80px; height: 80px;'):
                    ui.html('<span class="material-symbols-outlined card-icon" style="font-size: 3rem;">analytics</span>')
                ui.html(f'<h1 class="card-title" style="font-size: 2.5rem; margin-bottom: 1rem;">Genetic Analysis Report</h1>')
                ui.html('<p class="card-description" style="max-width: 600px; margin: 0 auto 2rem; font-size: 1.1rem;">Comprehensive genomic analysis with personalized risk assessment and phenotype associations</p>')

                # User and Job Info with Metric Cards
                with ui.element('div').style('display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin-bottom: 1rem;'):
                    with ui.element('div').classes('metric-card').style('min-width: 150px;'):
                        ui.html(f'<div class="metric-value" style="font-size: 1.5rem;">👤 {report["user_id"]}</div>')
                        ui.html('<div class="metric-label">User ID</div>')
                    with ui.element('div').classes('metric-card').style('min-width: 150px;'):
                        ui.html(f'<div class="metric-value" style="font-size: 1.5rem;">🔬 {report["job_id"]}</div>')
                        ui.html('<div class="metric-label">Job ID</div>')

        # Enhanced Container for Tabs and Content
        with ui.element('div').style('padding: 2rem;'):
            # Enhanced Modern Tabs
                with ui.element('div').classes('modern-tabs').style('''
                    background: var(--gray-100);
                    border-radius: var(--radius-xl);
                    padding: 1rem;
                    margin: 0 0 3rem 0;
                    box-shadow: var(--shadow-sm);
                '''):
                    with ui.tabs().classes('w-full') as tabs:
                        one = ui.tab('🧬 Genetic Risk Analysis').classes('modern-tab').style('''
                            padding: 1.25rem 2rem;
                            font-weight: 700;
                            font-size: 1rem;
                            border-radius: var(--radius-lg);
                            transition: var(--transition-base);
                        ''')
                        two = ui.tab('🎯 Integrated Risk Profile').classes('modern-tab').style('''
                            padding: 1.25rem 2rem;
                            font-weight: 700;
                            font-size: 1rem;
                            border-radius: var(--radius-lg);
                            transition: var(--transition-base);
                        ''')
                        three = ui.tab('🔬 PheWAS Analysis').classes('modern-tab').style('''
                            padding: 1.25rem 2rem;
                            font-weight: 700;
                            font-size: 1rem;
                            border-radius: var(--radius-lg);
                            transition: var(--transition-base);
                        ''')

                with ui.tab_panels(tabs, value=one).classes('w-full'):
                    # Enhanced Genetic Risk Tab
                    with ui.tab_panel(one):
                        with ui.element('div').classes('section-title').style('margin-bottom: 2.5rem;'):
                            ui.label('🧬 Genetic Risk Assessment')

                        explanation = report['explanations']['genetic_risk']

                        # Enhanced Statistical Summary
                        statistical_summary = explanation.get('statistical_summary')
                    if statistical_summary:
                        with ui.element('div').classes('info-card genetic-risk').style('''
                            background: linear-gradient(135deg, var(--primary-50) 0%, rgba(255,255,255,0.9) 100%);
                            border: 1px solid var(--primary-200);
                            border-left: 6px solid var(--primary-600);
                            margin-bottom: 2rem;
                        '''):
                            with ui.element('div').classes('card-header'):
                                with ui.element('div').classes('card-icon-container'):
                                    ui.html('<span class="material-symbols-outlined card-icon">analytics</span>')
                                ui.html('<h3 class="card-title">Statistical Summary</h3>')
                            for line in statistical_summary:
                                ui.html(f'<div class="highlight-box" style="margin: 1rem 0; padding: 1rem; border-left: 4px solid var(--primary-400);">• {line}</div>')

                    # Enhanced Interpretation & Advice
                    with ui.element('div').classes('info-card genetic-risk').style('''
                        background: linear-gradient(135deg, var(--primary-100) 0%, rgba(255,255,255,0.9) 100%);
                        border: 1px solid var(--primary-300);
                        border-left: 6px solid var(--primary-700);
                        margin-bottom: 2rem;
                    '''):
                        with ui.element('div').classes('card-header'):
                            with ui.element('div').classes('card-icon-container'):
                                ui.html('<span class="material-symbols-outlined card-icon">lightbulb</span>')
                            ui.html('<h3 class="card-title">Clinical Interpretation & Recommendations</h3>')
                        ui.html(f'''
                            <div class="highlight-box" style="margin: 1rem 0; padding: 1.5rem; background: rgba(255,255,255,0.7); border-radius: var(--radius-lg);">
                                <div style="margin-bottom: 1rem;"><strong style="color: var(--primary-800);">Summary:</strong> {explanation.get("summary", "N/A")}</div>
                                <div style="margin-bottom: 1rem;"><strong style="color: var(--primary-800);">Clinical Details:</strong> {explanation.get("details", "N/A")}</div>
                                <div><strong style="color: var(--primary-800);">Medical Advice:</strong> {explanation.get("advice", "N/A")}</div>
                            </div>
                        ''')
                    
                    # Enhanced Raw Text Section
                    raw_text = explanation.get('raw_text')
                    if raw_text:
                        with ui.expansion('📄 View Raw Analysis Results', icon='description').classes('w-full').style('''
                            background: rgba(255,255,255,0.8);
                            border: 1px solid var(--gray-200);
                            border-radius: var(--radius-lg);
                            margin-bottom: 2rem;
                        '''):
                            with ui.element('div').classes('info-card').style('background: transparent; box-shadow: none; border: none; padding: 1rem;'):
                                for line in raw_text:
                                    ui.html(f'<div class="highlight-box" style="margin: 0.5rem 0; padding: 0.75rem; font-family: monospace; font-size: 0.9rem;">• {line}</div>')
                    
                    # Enhanced Visualizations Section
                    with ui.element('div').classes('section-title').style('margin: 3rem 0 2rem 0; display: flex; align-items: center; gap: 1rem;'):
                        with ui.element('div').classes('card-icon-container').style('width: 60px; height: 60px;'):
                            ui.html('<span class="material-symbols-outlined card-icon">bar_chart</span>')
                        ui.html('<h3 style="margin: 0; color: var(--primary-900); font-weight: 800; font-size: 1.5rem;">Risk Distribution Visualizations</h3>')
                    
                    with ui.row().classes('w-full gap-6'):
                        prs_dist_fig = report['visualizations'].get('prs_distribution')
                        if prs_dist_fig:
                            with ui.element('div').classes('plot-container').style('width: 100%; display: flex; justify-content: center; align-items: center;'):
                                ui.plotly(prs_dist_fig).classes('w-full').style('max-width: 900px;')
                        
                        prs_curve_fig = report['visualizations'].get('prs_curve')
                        if prs_curve_fig:
                            with ui.element('div').classes('plot-container').style('width: 100%; display: flex; justify-content: center; align-items: center;'):
                                ui.plotly(prs_curve_fig).classes('w-full').style('max-width: 900px;')

                # Enhanced Integrated Risk Tab
                with ui.tab_panel(two):
                    with ui.element('div').classes('section-title').style('margin-bottom: 2.5rem;'):
                        ui.label('🎯 Integrated Disease Risk Assessment')
                    
                    explanation = report['explanations']['integrated_risk']

                    # Enhanced Statistical Summary for Integrated Risk
                    statistical_summary_integrated = explanation.get('statistical_summary')
                    if statistical_summary_integrated:
                        with ui.element('div').classes('info-card integrated-risk').style('''
                            background: linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(255,255,255,0.9) 100%);
                            border: 1px solid rgba(59, 130, 246, 0.2);
                            border-left: 6px solid var(--primary-600);
                            margin-bottom: 2rem;
                        '''):
                            with ui.element('div').classes('card-header'):
                                with ui.element('div').classes('card-icon-container'):
                                    ui.html('<span class="material-symbols-outlined card-icon">analytics</span>')
                                ui.html('<h3 class="card-title">Statistical Summary</h3>')
                            for line in statistical_summary_integrated:
                                ui.html(f'<div class="highlight-box" style="margin: 1rem 0; padding: 1rem; border-left: 4px solid var(--primary-500);">• {line}</div>')

                    # Enhanced Interpretation & Advice for Integrated Risk
                    with ui.element('div').classes('info-card integrated-risk').style('''
                        background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(255,255,255,0.9) 100%);
                        border: 1px solid rgba(59, 130, 246, 0.3);
                        border-left: 6px solid var(--primary-700);
                        margin-bottom: 2rem;
                    '''):
                        with ui.element('div').classes('card-header'):
                            with ui.element('div').classes('card-icon-container'):
                                ui.html('<span class="material-symbols-outlined card-icon">lightbulb</span>')
                            ui.html('<h3 class="card-title">Clinical Interpretation & Recommendations</h3>')
                        ui.html(f'''
                            <div class="highlight-box" style="margin: 1rem 0; padding: 1.5rem; background: rgba(255,255,255,0.7); border-radius: var(--radius-lg);">
                                <div style="margin-bottom: 1rem;"><strong style="color: var(--primary-800);">Overall Summary:</strong> {explanation.get("summary", "N/A")}</div>
                                <div style="margin-bottom: 1rem;"><strong style="color: var(--primary-800);">Risk Details:</strong> {explanation.get("details", "N/A")}</div>
                                <div><strong style="color: var(--primary-800);">Clinical Recommendations:</strong> {explanation.get("advice", "N/A")}</div>
                            </div>
                        ''')

                    # Enhanced Raw Text Section for Integrated Risk
                    raw_text_integrated = report['explanations']['integrated_risk'].get('raw_text')
                    if raw_text_integrated:
                        with ui.expansion('📄 View Raw Integration Results', icon='integration_instructions').classes('w-full').style('''
                            background: rgba(255,255,255,0.8);
                            border: 1px solid var(--gray-200);
                            border-radius: var(--radius-lg);
                            margin-bottom: 2rem;
                        '''):
                            with ui.element('div').classes('info-card').style('background: transparent; box-shadow: none; border: none; padding: 1rem;'):
                                for line in raw_text_integrated:
                                    ui.html(f'<div class="highlight-box" style="margin: 0.5rem 0; padding: 0.75rem; font-family: monospace; font-size: 0.9rem;">• {line}</div>')

                    # Enhanced Visualizations Section for Integrated Risk
                    ui.html('''
                        <div style="margin: 3rem 0 2rem 0;">
                            <div class="section-title" style="display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem;">
                                <div style="font-size: 2rem;">📈</div>
                                <h4 style="margin: 0; color: var(--primary-900); font-weight: 800; font-size: 1.5rem;">
                                    Integrated Risk Visualizations
                                </h4>
                            </div>
                        </div>
                    ''')
                    
                    with ui.row().classes('w-full gap-6'):
                        risk_score_dist_fig = report['visualizations'].get('risk_score_distribution')
                        if risk_score_dist_fig:
                            with ui.element('div').classes('plot-container').style('width: 100%; display: flex; justify-content: center; align-items: center;'):
                                ui.plotly(risk_score_dist_fig).classes('w-full').style('max-width: 900px;')

                        risk_curve_fig = report['visualizations'].get('risk_curve')
                        if risk_curve_fig:
                            with ui.element('div').classes('plot-container').style('width: 100%; display: flex; justify-content: center; align-items: center;'):
                                ui.plotly(risk_curve_fig).classes('w-full').style('max-width: 900px;')

                # Enhanced PheWAS Tab
                with ui.tab_panel(three):
                    with ui.element('div').classes('section-title').style('margin-bottom: 2.5rem;'):
                        ui.label('🔬 Phenome-Wide Association Study (PheWAS)')
                    
                    phewas_exp = report['explanations'].get('phewas')
                    if phewas_exp and isinstance(phewas_exp, dict):
                        # Enhanced Summary Section
                        with ui.element('div').classes('info-card phewas').style('''
                            background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(255,255,255,0.9) 100%);
                            border: 1px solid rgba(16, 185, 129, 0.2);
                            border-left: 6px solid var(--accent-500);
                            margin-bottom: 2rem;
                        '''):
                            with ui.element('div').classes('card-header'):
                                with ui.element('div').classes('card-icon-container'):
                                    ui.html('<span class="material-symbols-outlined card-icon">assignment</span>')
                                ui.html('<h3 class="card-title">PheWAS Analysis Summary</h3>')
                            ui.html(f'<div class="highlight-box" style="margin: 1rem 0; padding: 1.5rem; background: rgba(255,255,255,0.7); border-radius: var(--radius-lg);">{phewas_exp.get("summary", "N/A")}</div>')
                        
                        # Enhanced Methodology Section
                        with ui.element('div').classes('info-card').style('''
                            background: linear-gradient(135deg, var(--gray-50) 0%, rgba(255,255,255,0.9) 100%);
                            border: 1px solid var(--gray-200);
                            border-left: 6px solid var(--gray-600);
                            margin-bottom: 2rem;
                        '''):
                            with ui.element('div').classes('card-header'):
                                with ui.element('div').classes('card-icon-container'):
                                    ui.html('<span class="material-symbols-outlined card-icon">science</span>')
                                ui.html('<h3 class="card-title">Analysis Methodology</h3>')
                            ui.html(f'<div class="highlight-box" style="margin: 1rem 0; padding: 1.5rem; background: rgba(255,255,255,0.7); border-radius: var(--radius-lg);">{phewas_exp.get("methodology", "N/A")}</div>')
                        
                        # Enhanced Significant Findings Section
                        significant_findings = phewas_exp.get('significant_findings', [])
                        if significant_findings:
                            with ui.element('div').classes('info-card warning').style('''
                                background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(255,255,255,0.9) 100%);
                                border: 1px solid rgba(245, 158, 11, 0.2);
                                border-left: 6px solid var(--warning-500);
                                margin-bottom: 2rem;
                            '''):
                                with ui.element('div').classes('card-header'):
                                    with ui.element('div').classes('card-icon-container'):
                                        ui.html('<span class="material-symbols-outlined card-icon">warning</span>')
                                    ui.html('<h3 class="card-title">Significant Genetic Associations</h3>')
                                for finding in significant_findings:
                                    ui.html(f'''
                                        <div class="highlight-box" style="margin: 1.5rem 0; padding: 1.5rem; border-left: 4px solid var(--warning-500); background: rgba(255,255,255,0.8); border-radius: var(--radius-lg);">
                                            <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                                                <div style="font-size: 1.2rem; font-weight: 700; color: var(--warning-600);">{finding.get("phenotype", "Unknown")}</div>
                                                <div class="badge warning" style="font-size: 0.75rem;">{finding.get("effect_direction", "N/A")}</div>
                                            </div>
                                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; font-size: 0.95rem;">
                                                <div><strong style="color: var(--gray-700);">P-value:</strong> {finding.get("p_value", "N/A")}</div>
                                                <div><strong style="color: var(--gray-700);">Clinical Relevance:</strong> {finding.get("clinical_relevance", "N/A")}</div>
                                            </div>
                                        </div>
                                    ''')
                        else:
                            with ui.element('div').classes('info-card phewas').style('''
                                background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(255,255,255,0.9) 100%);
                                border: 1px solid rgba(16, 185, 129, 0.2);
                                border-left: 6px solid var(--accent-500);
                                margin-bottom: 2rem;
                            '''):
                                ui.html('''
                                    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
                                        <div style="font-size: 2rem;">✅</div>
                                        <h4 style="margin: 0; color: var(--primary-900); font-weight: 800; font-size: 1.25rem;">
                                            Genetic Association Results
                                        </h4>
                                    </div>
                                ''')
                                ui.html('<div class="highlight-box" style="margin: 1rem 0; padding: 1.5rem; background: rgba(255,255,255,0.7); border-radius: var(--radius-lg);">No statistically significant associations identified after multiple testing correction.</div>')
                        
                        # Enhanced Clinical Implications
                        with ui.element('div').classes('info-card').style('''
                            background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(255,255,255,0.9) 100%);
                            border: 1px solid rgba(59, 130, 246, 0.15);
                            border-left: 6px solid var(--primary-500);
                            margin-bottom: 2rem;
                        '''):
                            ui.html('''
                                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
                                    <div style="font-size: 2rem;">🏥</div>
                                    <h4 style="margin: 0; color: var(--primary-900); font-weight: 800; font-size: 1.25rem;">
                                        Clinical Implications
                                    </h4>
                                </div>
                            ''')
                            ui.html(f'<div class="highlight-box" style="margin: 1rem 0; padding: 1.5rem; background: rgba(255,255,255,0.7); border-radius: var(--radius-lg);">{phewas_exp.get("clinical_implications", "N/A")}</div>')
                        
                        # Enhanced Recommendations
                        recommendations = phewas_exp.get('recommendations', [])
                        if recommendations:
                            with ui.element('div').classes('info-card phewas').style('''
                                background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(255,255,255,0.9) 100%);
                                border: 1px solid rgba(16, 185, 129, 0.2);
                                border-left: 6px solid var(--accent-500);
                                margin-bottom: 2rem;
                            '''):
                                ui.html('''
                                    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
                                        <div style="font-size: 2rem;">💊</div>
                                        <h4 style="margin: 0; color: var(--primary-900); font-weight: 800; font-size: 1.25rem;">
                                            Clinical Recommendations
                                        </h4>
                                    </div>
                                ''')
                                for rec in recommendations:
                                    ui.html(f'<div class="highlight-box" style="margin: 1rem 0; padding: 1rem; border-left: 4px solid var(--accent-400);">• {rec}</div>')
                        
                        # Enhanced Limitations Section
                        with ui.element('div').classes('info-card error').style('''
                            background: linear-gradient(135deg, rgba(239, 68, 68, 0.05) 0%, rgba(255,255,255,0.9) 100%);
                            border: 1px solid rgba(239, 68, 68, 0.15);
                            border-left: 6px solid var(--error-500);
                            margin-bottom: 2rem;
                        '''):
                            ui.html('''
                                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
                                    <div style="font-size: 2rem;">⚠️</div>
                                    <h4 style="margin: 0; color: var(--primary-900); font-weight: 800; font-size: 1.25rem;">
                                        Important Study Limitations
                                    </h4>
                                </div>
                            ''')
                            ui.html(f'<div class="highlight-box" style="margin: 1rem 0; padding: 1.5rem; background: rgba(255,255,255,0.7); border-radius: var(--radius-lg);">{phewas_exp.get("limitations", "N/A")}</div>')
                            
                    elif phewas_exp:
                        # Fallback for old string format
                        with ui.element('div').classes('info-card'):
                            ui.html(f'<div class="highlight-box">{phewas_exp}</div>')
                    else:
                        with ui.element('div').classes('info-card'):
                            ui.html('<div class="highlight-box">No PheWAS analysis available.</div>')
                    
                    # Enhanced Data Visualization Section
                    ui.html('''
                        <div style="margin: 3rem 0 2rem 0;">
                            <div class="section-title" style="display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem;">
                                <div style="font-size: 2rem;">📊</div>
                                <h4 style="margin: 0; color: var(--primary-900); font-weight: 800; font-size: 1.5rem;">
                                    PheWAS Results Visualization
                                </h4>
                            </div>
                        </div>
                    ''')
                    
                    # Enhanced PheWAS Table
                    phewas_table = report['visualizations'].get('phewas_table')
                    if phewas_table:
                        with ui.expansion('📊 View Detailed PheWAS Results Table', icon='table_view').classes('w-full').style('''
                            background: rgba(255,255,255,0.9);
                            border: 1px solid var(--gray-200);
                            border-radius: var(--radius-lg);
                            margin-bottom: 2rem;
                            box-shadow: var(--shadow-sm);
                        '''):
                            ui.table(columns=[{'name': k, 'label': k.replace('_', ' ').title(), 'field': k, 'sortable': True} for k in phewas_table[0].keys()],
                                     rows=phewas_table,
                                     pagination=10).classes('w-full modern-table').style('''
                                border-radius: var(--radius-md);
                                overflow: hidden;
                                /* Ensure table header background is visible on scroll */
                                position: relative;
                                z-index: 1;
                            ''')

                    # Enhanced PheWAS Plot
                    phewas_plot_fig = report['visualizations'].get('phewas_plot')
                    if phewas_plot_fig:
                        with ui.element('div').classes('plot-container').style('width: 100%; display: flex; justify-content: center; align-items: center; margin-bottom: 2rem;'):
                            ui.plotly(phewas_plot_fig).classes('w-full').style('max-width: 1200px;')

# Mobile navigation handler
def toggle_mobile_nav():
    """Toggle mobile navigation menu"""
    mobile_nav = ui.query('.mobile-nav').first()
    if mobile_nav:
        mobile_nav.classes.toggle('show')

# Main UI Layout
with ui.element('div').style('min-height: 100vh; width: 100vw; display: flex; flex-direction: column; align-items: center; padding: 0; margin: 0;'):
    
    # Top Navigation Bar - similar to biomni.stanford.edu
    with ui.element('nav').classes('top-navbar'):
        # Brand/Logo section
        with ui.element('div').classes('navbar-brand'):
            ui.html('<span class="material-symbols-outlined navbar-brand-icon">sort</span>')
            ui.html('<a href="#" class="navbar-brand-link">Spectral Ranking</a>')
        
        # Main navigation menu (hidden on mobile)
        with ui.element('ul').classes('navbar-nav'):
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="/dashboard" class="nav-link">Dashboard</a>')
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="#mode-selection" class="nav-link active">Analysis</a>')
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="#results" class="nav-link">Results</a>')
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="#documentation" class="nav-link">Help</a>')
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="#about" class="nav-link">About</a>')
        
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
                    ui.html('<a href="/dashboard" class="nav-link">Dashboard</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#mode-selection" class="nav-link active">Analysis</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#results" class="nav-link">Results</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#documentation" class="nav-link">Help</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#about" class="nav-link">About</a>')
            
            with ui.element('div').classes('navbar-actions'):
                ui.html('<a href="https://github.com/MaxineYu/Spectral_Ranking" class="nav-button primary" target="_blank"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/github/github-original.svg" alt="GitHub" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle; filter: brightness(0) invert(1);"/>GitHub</a>')
                ui.html('<a href="https://doi.org/10.1287/opre.2023.0439" class="nav-button primary" target="_blank"><img src="https://arxiv.org/static/browse/0.3.4/images/arxiv-logo-one-color-white.svg" alt="arXiv" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle; filter: brightness(0) invert(1);"/>Read the Paper</a>')
    # Enhanced Hero Section with Modern Design - Full screen background
    with ui.element('div').classes('hero-section').style('margin: 0 -1rem; width: calc(100% + 2rem);'):
        # Add floating particles background
        ui.html('''
            <div class="hero-floating-particles">
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
                <div class="particle"></div>
            </div>
            <div class="hero-glow"></div>
        ''')
        
        with ui.element('div').classes('hero-content'):
            # Enhanced Title with UPenn Shield (aligned left of PRSAgent, vertically centered)
            ui.html('''
                <div class="hero-title" style="display: flex; align-items: center; justify-content: center; gap: 1rem;">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/7/7c/Shield_of_the_University_of_Pennsylvania.svg" alt="UPenn Shield" style="height: 3.2rem; width: auto; display: block; margin: 0; padding: 0;"/>
                    <span style="font-weight: 900; font-size: clamp(2.5rem, 5vw, 4rem); line-height: 1.1; color: #fff; font-family: 'Inter', 'Georgia', serif;">  Robust Spectral Ranking</span>
                    <img src="https://static.cdnlogo.com/logos/w/18/washington-university-in-st-louis.svg" alt="WUSTL Shield" style="height: 4.8rem; width: auto; display: block; margin: 0; padding: 0;"/>
                </div>
            ''')
            
            # Enhanced Subtitle
            ui.html('''
                <div class="hero-subtitle">
                    An advanced statistical framework for robust ranking and uncertainty quantification based on pairwise or multiway comparisons.
                </div>
            ''')
            
            # New Feature Highlights
            ui.html('''
                <div class="hero-features">
                    <div class="hero-feature">
                        <span class="material-symbols-outlined hero-feature-icon">biotech</span>
                        <div class="hero-feature-title">Spectral Method</div>
                        <div class="hero-feature-description">
                            Utilizes a powerful spectral method to derive robust rankings from complex, heterogeneous comparison data.
                        </div>
                    </div>
                    <div class="hero-feature">
                        <span class="material-symbols-outlined hero-feature-icon">balance</span>
                        <div class="hero-feature-title">Uncertainty Quantification</div>
                        <div class="hero-feature-description">
                            Employs weighted bootstrap to construct confidence intervals, assessing the reliability and stability of ranks.
                        </div>
                    </div>
                    <div class="hero-feature">
                        <span class="material-symbols-outlined hero-feature-icon">public</span>
                        <div class="hero-feature-title">Broad Applicability</div>
                        <div class="hero-feature-description">
                           Applicable to diverse fields like machine learning, sports analytics, market research, and academic journal rankings.
                        </div>
                    </div>
                </div>
            ''')
            
            # Call-to-Action
            ui.html('''
                <div class="hero-cta">
                    <a href="#mode-selection" class="hero-cta-button" style="background: #fff !important; color: #011f5b !important; border: 2.5px solid #011f5b; font-weight: 900; font-size: 1.1rem; transition: background 0.2s, color 0.2s, box-shadow 0.2s; box-shadow: 0 4px 16px rgba(1,31,91,0.10);">
                        Start Analysis
                    </a>
                </div>
            ''')

    # Main Container - positioned after full-screen hero
    with ui.element('div').style('width: 100%; max-width: 1400px; margin: 0 auto; padding: 40px 1rem 0 1rem; position: relative; z-index: 2;'):
        
        # Mode Selection Cards (side-by-side) between hero and analysis
        with ui.element('div').style('display: flex; gap: 2rem; margin: 0rem auto; max-width: 1400px; justify-content: center; flex-wrap: wrap;').props('id="mode-selection"'):
            # Agent Mode (Left)
            with ui.element('div').classes('mode-card active').props('id="agent-mode-card"') as agent_mode_card:
                ui.html('''
                    <div class="card-content">
                        <div class="card-icon-wrapper"><span class="material-symbols-outlined">chat_bubble</span></div>
                        <h3 class="card-title">Agent Mode</h3>
                        <p class="card-description">
                            Chat with AI assistant to configure analysis parameters and get intelligent recommendations
                        </p>
                        <ul class="card-features">
                            <li><span class="material-symbols-outlined">smart_toy</span> AI-Powered Configuration</li>
                            <li><span class="material-symbols-outlined">chat</span> Interactive Guidance</li>
                            <li><span class="material-symbols-outlined">auto_fix_high</span> Automated Suggestions</li>
                        </ul>
                    </div>
                ''')

            # Manual Mode (Right)
            with ui.element('div').classes('mode-card inactive').props('id="manual-mode-card"') as manual_mode_card:
                ui.html('''
                    <div class="card-content">
                        <div class="card-icon-wrapper"><span class="material-symbols-outlined">build</span></div>
                        <h3 class="card-title">Manual Mode</h3>
                        <p class="card-description">
                            Manually configure all analysis parameters with full control over every setting
                        </p>
                        <ul class="card-features">
                            <li><span class="material-symbols-outlined">tune</span> Full Parameter Control</li>
                            <li><span class="material-symbols-outlined">precision_manufacturing</span> Precise Configuration</li>
                            <li><span class="material-symbols-outlined">settings</span> Advanced Options</li>
                        </ul>
                    </div>
                ''')

        # Agent Mode Analysis Section (initially hidden)
        agent_analysis_section = ui.element('section').style('width: 100%; max-width: 1400px; margin: 1rem auto; padding: 0; height: 90vh; display: none;').props('id="agent-analysis"')

        with agent_analysis_section:
            with ui.element('div').classes('info-card').style('text-align: center; margin: 0; border: 3px solid #011f5b; height: 100%;'):
                # Main layout: Left 2/3 for data upload/preview, Right 1/3 for chat
                with ui.element('div').classes('agent-layout').style('display: flex; height: 100%; gap: 1rem;'):
                    # Left side: Data upload and preview area (2/3 width)
                    data_area = ui.element('div').style('''
                        flex: 2;
                        background: rgba(255,255,255,0.95);
                        border-radius: var(--radius-lg);
                        padding: 1.5rem;
                        display: flex;
                        flex-direction: column;
                        gap: 1rem;
                        border: 1px solid var(--gray-200);
                        overflow: hidden;
                    ''')

                    # Right side: Chat interface (1/3 width)
                    chat_container = ui.element('div').classes('agent-chat-container').style('''
                        flex: 1;
                        background: rgba(255,255,255,0.95);
                        border-radius: var(--radius-lg);
                        border: 1px solid var(--gray-200);
                        padding: 0;
                        display: flex;
                        flex-direction: column;
                        box-shadow: none;
                        backdrop-filter: blur(10px);
                    ''')

                    # Data upload and preview area content
                    with data_area:
                        # File upload section
                        with ui.element('div').style('margin-bottom: 0.5rem;'):
                            # File upload area - taller for better text fit
                            agent_upload_area = ui.element('div').props('id="agent-upload-area"').style('margin: 0; max-width: 100%; position: relative; height: 75px; cursor: pointer; border: 2px dashed #011f5b; border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; background: rgba(1, 31, 91, 0.1); transition: all 0.3s ease;')
                            with agent_upload_area:
                                ui.html('''
                                    <div id="agent-upload-content" style="text-align: center; color: #011f5b; padding: 0.5rem 0;">
                                        <span class="material-symbols-outlined" style="font-size: 1.2rem; margin-bottom: 0.25rem; display: block; color: #011f5b;">upload_file</span>
                                        <div style="font-weight: 600; font-size: 0.8rem;">Upload CSV</div>
                                        <div style="font-size: 0.7rem; color: #666; margin-top: 0.1rem;">Click or drag file</div>
                                    </div>
                                ''')
                                agent_file_input = ui.upload(on_upload=lambda e: handle_agent_file_upload(e, messages_container, input_field), multiple=False, auto_upload=True).props('accept=.csv').style('position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; z-index: 10; cursor: pointer;')
                            agent_upload_area.on('click', lambda: agent_file_input.run_method('pickFiles'))

                        # Data preview section - full space without title
                        with ui.element('div').style('flex: 1; display: flex; flex-direction: column;'):
                            # Data preview container - expanded space
                            data_preview_container = ui.element('div').style('''
                                flex: 1;
                                background: var(--gray-50);
                                border-radius: var(--radius-lg);
                                border: 1px solid var(--gray-200);
                                padding: 1rem;
                                overflow: auto;
                                overflow-x: auto;
                                overflow-y: auto;
                                min-height: 400px;
                                max-height: calc(100vh - 300px);
                                overscroll-behavior: contain;
                                -webkit-overflow-scrolling: touch;
                            ''').classes('data-preview-container')

                            # Bind global ref for agent mode report display
                            try:
                                agent_data_preview_ref = data_preview_container
                                print(f"DEBUG: agent_data_preview_ref set to: {agent_data_preview_ref}")
                            except Exception as e:
                                print(f"DEBUG: error setting agent_data_preview_ref: {e}")
                                pass

                            with data_preview_container.classes('data-preview-container'):
                                ui.html('''
                                    <div style="text-align: center; color: var(--gray-600); padding: 1rem;">
                                        <span class="material-symbols-outlined" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block;">description</span>
                                        <div style="font-weight: 600; margin-bottom: 0.5rem; font-size: 0.9rem;">No Data Uploaded</div>
                                        <div style="font-size: 0.8rem;">Click above to upload CSV file</div>
                                    </div>
                                ''')

                    with chat_container:
                        # Add padding wrapper for content - responsive to height changes
                        with ui.element('div').style('padding: 1rem; height: 100%; display: flex; flex-direction: column; gap: 0.5rem;'):
                            # Chat header - compact for height responsiveness
                            with ui.element('div').style('display: flex; justify-content: center; margin-bottom: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--gray-200); flex-shrink: 0;'):
                                ui.html('<h4 style="color: var(--primary-900); margin: 0; font-weight: 800; font-size: 1rem;">Chat Assistant</h4>')

                            # Messages container - flexible height adaptation
                            messages_container = ui.element('div').classes('chat-messages').style('''
                                flex: 1;
                                overflow-y: auto;
                                padding: 0.5rem;
                                background: var(--gray-50);
                                border-radius: var(--radius-lg);
                                min-height: max(200px, 40vh);
                                max-height: calc(100vh - 200px);
                                overscroll-behavior: contain;
                            ''')

                            # Welcome message
                            with messages_container:
                                with ui.element('div').classes('message assistant').style('''
                                    display: flex;
                                    gap: 0.75rem;
                                    margin-bottom: 1rem;
                                    align-items: flex-start;
                                '''):
                                    ui.html('<div class="message-avatar" style="background: #011f5b; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0;"><span class="material-symbols-outlined" style="font-size: 1.2rem;">support_agent</span></div>')
                                    with ui.element('div').classes('message-content').style('flex: 1;'):
                                        ui.html('<div class="message-text" style="background: white; padding: 0.75rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200); font-size: 0.9rem; line-height: 1.5;">Hello! I\'m here to help you configure your spectral ranking analysis. Please upload a CSV file with your performance data, and I\'ll guide you through the process.</div>')

                            # Smart suggestions area
                            suggestions_area = ui.element('div').classes('chat-suggestions').props('id="chat-suggestions"').style('''
                                margin-bottom: 0.75rem;
                                padding: 0.75rem;
                                background: rgba(1, 31, 91, 0.05);
                                border-radius: var(--radius-md);
                                border: 1px solid rgba(1, 31, 91, 0.1);
                                flex-shrink: 0;
                            ''')
                            # Bind global ref for suggestions area
                            try:
                                suggestions_area_ref = suggestions_area
                            except Exception:
                                pass

                            # Input area - compact and flexible (only text input and send button)
                            with ui.element('div').classes('chat-input-area').style('display: flex; gap: 0.75rem; align-items: flex-end; flex-shrink: 0;'):
                                # Send button with explicit Material Symbols icon
                                send_button = ui.html('''
                                    <button id="send-button" class="q-btn q-btn-round q-btn--primary q-btn--actionable q-hoverable q-focusable"
                                            style="height: 40px; width: 40px; flex-shrink: 0; border-radius: 50%; background: #011f5b; border: none; color: white; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                                        <span class="material-symbols-outlined" style="font-size: 1.2rem;">send</span>
                                    </button>
                                ''').on('click', lambda: send_agent_message(input_field, messages_container, status_area))

                                # Text input
                                input_field = ui.textarea(
                                    label='Type your message...',
                                    placeholder='Ask questions about your data or analysis...'
                                ).props('rows=2').style('flex: 1;').on('keydown', lambda e: handle_enter_key(e, input_field, messages_container, status_area, send_button))

                            # Status area - minimal spacing
                            status_area = ui.element('div').style('margin-top: 0.25rem; font-size: 0.85rem; color: var(--gray-600); text-align: center; flex-shrink: 0;')
                    chat_state = {
                        'messages': [{'role': 'assistant', 'content': 'Hello! I\'m here to help you configure your spectral ranking analysis. Please upload a CSV file with your performance data, and I\'ll guide you through the process.'}],
                        'uploaded_file_id': None,
                        'current_job_id': None
                    }

        def switch_to_agent():
            # Show agent mode content
            ui.run_javascript('document.getElementById("agent-analysis").style.display = "block";')
            ui.run_javascript('document.getElementById("analysis").style.display = "none";')

            # Keep report container available for agent mode results

            # Update card styles
            ui.run_javascript('''
                const agentCard = document.getElementById("agent-mode-card");
                const manualCard = document.getElementById("manual-mode-card");
                agentCard.classList.add("active");
                agentCard.classList.remove("inactive");
                manualCard.classList.add("inactive");
                manualCard.classList.remove("active");
            ''')

            # Scroll to AI Assistant section (slightly above center)
            ui.run_javascript('''
                const element = document.getElementById("agent-analysis");
                const elementRect = element.getBoundingClientRect();
                const absoluteElementTop = elementRect.top + window.pageYOffset;
                const middle = absoluteElementTop - (window.innerHeight / 2) + (element.offsetHeight / 2);
                window.scrollTo({top: middle - 20, behavior: "smooth"});
            ''')

        def switch_to_manual():
            # Show manual mode content
            ui.run_javascript('document.getElementById("agent-analysis").style.display = "none";')
            ui.run_javascript('document.getElementById("analysis").style.display = "block";')

            # Keep report container available for manual mode results

            # Update card styles
            ui.run_javascript('''
                const agentCard = document.getElementById("agent-mode-card");
                const manualCard = document.getElementById("manual-mode-card");
                manualCard.classList.add("active");
                manualCard.classList.remove("inactive");
                agentCard.classList.add("inactive");
                agentCard.classList.remove("active");
            ''')

            # Scroll to Generate Analysis Report section (slightly below AI Assistant position)
            ui.run_javascript('''
                const element = document.getElementById("analysis");
                const elementRect = element.getBoundingClientRect();
                const absoluteElementTop = elementRect.top + window.pageYOffset;
                const middle = absoluteElementTop - (window.innerHeight / 2) + (element.offsetHeight / 2);
                window.scrollTo({top: middle - 30, behavior: "smooth"});
            ''')

        # Set initial state using JavaScript on page load
        ui.add_head_html('''
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Initial state: Agent Mode active
            var agentAnalysisSection = document.getElementById("agent-analysis");
            var analysisSection = document.getElementById("analysis");
            var resultsSection = document.getElementById("results");
            if (agentAnalysisSection) {
                agentAnalysisSection.style.display = "block";
            }
            if (analysisSection) analysisSection.style.display = "none";
            if (resultsSection) resultsSection.style.display = "none";

            // Set initial card styles (Agent Mode active, Manual Mode inactive)
            var agentCard = document.getElementById("agent-mode-card");
            var manualCard = document.getElementById("manual-mode-card");
            if (agentCard) {
                agentCard.classList.add("active");
                agentCard.classList.remove("inactive");
            }
            if (manualCard) {
                manualCard.classList.add("inactive");
                manualCard.classList.remove("active");
            }
        });
        </script>
        ''')

        agent_mode_card.on('click', switch_to_agent)
        manual_mode_card.on('click', switch_to_manual)

        # Query Section with Enhanced Design
        with ui.element('section').style('width: 100%; max-width: 1400px; margin: 1rem auto; padding: 0; height: 90vh;').props('id="analysis"'):
            with ui.element('div').classes('info-card').style('text-align: center; margin: 0; border: 3px solid #011f5b; height: 100%;'):
                ui.html('''
                    <div style="margin-bottom: 0rem;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 1rem; margin-bottom: 1.5rem;">
                            <span class="material-symbols-outlined" style="font-size: 2rem;">search</span>
                            <h2 style="color: var(--primary-900); font-weight: 800; margin: 0; font-size: 1.5rem;">Generate Analysis Report</h2>
                        </div>
                        <p style="color: var(--gray-600); font-size: 0.9rem; max-width: 1000px; margin: 0 auto; line-height: 1.6;">
                            Upload your CSV file with performance data to generate a robust ranking analysis.
                        </p>
                    </div>
                ''')

                # Define uploaded_state and handle_upload function here
                uploaded_state = {'name': None, 'content': None}
                def handle_upload(e):
                    try:
                        content = e.content.read() if hasattr(e.content, 'read') else e.content
                    except Exception:
                        content = e.content
                    uploaded_state['name'] = e.name or 'data.csv'
                    uploaded_state['content'] = content

                    # Update upload area to show uploaded state
                    ui.run_javascript(f'''
                        const uploadArea = document.getElementById('manual-upload-area');
                        const uploadContent = document.getElementById('manual-upload-content');
                        if (uploadArea && uploadContent) {{
                            uploadArea.classList.add('uploaded');
                            uploadContent.innerHTML = `
                                <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                                    <span class="material-symbols-outlined" style="font-size: 1.2rem;">check_circle</span>
                                    <div style="text-align: left;">
                                        <div style="font-weight: 600; font-size: 0.8rem; color: #e5e7eb;">File Uploaded</div>
                                        <div style="font-size: 0.7rem; color: #d1d5db; margin-top: 0.1rem;">{e.name}</div>
                                    </div>
                                    <button onclick="event.stopPropagation(); resetManualUpload()" class="upload-delete-btn">×</button>
                                </div>
                            `;
                        }}
                        document.getElementById("file-status").innerText = "{e.name}";
                    ''')

                # Build the input area with native NiceGUI components
                with ui.element('div').style('margin-top: 1.5rem;'):
                    with ui.element('div').style('display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem;'):
                        # CSV File Upload Card
                        with ui.element('div').classes('highlight-box').style('text-align: center; background: #011f5b; color: #fff; padding: 2rem; position: relative; min-height: 380px; display: flex; flex-direction: column;'):
                            with ui.element('div').style('display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #fff;'):
                                ui.html('<span class="material-symbols-outlined" style="font-size: 1.5rem;">upload_file</span>')
                                ui.html('<h4 style="color: #fff; margin: 0; font-weight: 800; font-size: 1.1rem;"><b>CSV File Upload</b></h4>')
                            ui.html('<p style="color: #fff; margin-bottom: 1.5rem;">Upload your CSV file containing method performance data</p>')
                            with ui.element('div').style('text-align: center;'):
                                with ui.element('div').style('margin-bottom: 1rem;'):
                                    ui.html('<span style="color: #fff; font-weight: 600; font-size: 0.9rem;">Selected: <span id="file-status" style="color: #e5e7eb;">No file selected</span></span>')

                                # Restore the original, good-looking upload area and fix the click handler
                                upload_area = ui.element('div').props('id="manual-upload-area"').style('margin: 0 auto; max-width: 250px; position: relative; height: 80px; cursor: pointer;')
                                with upload_area:
                                    ui.html('''
                                        <div id="manual-upload-content" style="background: rgba(255,255,255,0.1); border: 2px dashed #fff; border-radius: 0.75rem; padding: 1.5rem; position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;">
                                            <span style="color: #fff; font-weight: 600;">Click to Upload CSV</span>
                                        </div>
                                    ''')
                                    file_input = ui.upload(on_upload=handle_upload, multiple=False, auto_upload=True).props('accept=.csv').style('position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; z-index: 10; cursor: pointer;')
                                upload_area.on('click', lambda: file_input.run_method('pickFiles'))

                        # Analysis Parameters Card
                        with ui.element('div').classes('highlight-box').style('text-align: center; background: #011f5b; color: #fff; padding: 2rem; min-height: 380px; display: flex; flex-direction: column; justify-content: flex-start;'):
                            with ui.element('div').style('display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #fff;'):
                                ui.html('<span class="material-symbols-outlined" style="font-size: 1.5rem;">settings</span>')
                                ui.html('<h4 style="color: #fff; margin: 0; font-weight: 800; font-size: 1.1rem;"><b>Analysis Parameters</b></h4>')
                            ui.html('<p style="color: #fff; margin-bottom: 1.5rem;">Configure ranking algorithm settings</p>')
                            with ui.element('div').style('display: flex; flex-direction: column; gap: 1.5rem; text-align: left;'):
                                # Ranking Direction
                                with ui.element('div'):
                                    ui.label('Ranking Direction').style('color: #fff; font-weight: 600; font-size: 0.95rem; display: block; margin-bottom: 0.5rem; text-align: center;')
                                    
                                    # State for the custom toggle
                                    ranking_direction_state = {'value': 'False'}

                                    with ui.row().props('no-wrap').style('width: 100%; display: flex; justify-content: center;'):
                                        # "Lower is Better" button
                                        with ui.button('Lower values are better') as btn_lower:
                                            ui.tooltip('Use for metrics like Error Rate, where a lower number is better.')
                                        
                                        # "Higher is Better" button
                                        with ui.button('Higher values are better') as btn_higher:
                                            ui.tooltip('Use for metrics like Accuracy, where a higher number is better.')

                                    # Apply styles to look like a toggle
                                    btn_lower.props('rounded-l-lg rounded-r-none flat')
                                    btn_higher.props('rounded-l-none rounded-r-lg flat')

                                    def update_styles(value: str):
                                        ranking_direction_state['value'] = value
                                        if value == 'False':
                                            btn_lower.props('color=primary text-color=white')
                                            btn_lower.style('border: 2px solid white;')
                                            btn_higher.props('color=grey-3 text-color=grey-6')
                                            btn_higher.style('border: none;')
                                        else:
                                            btn_lower.props('color=grey-3 text-color=grey-6')
                                            btn_lower.style('border: none;')
                                            btn_higher.props('color=primary text-color=white')
                                            btn_higher.style('border: 2px solid white;')
                                    
                                    btn_lower.on('click', lambda: update_styles('False'))
                                    btn_higher.on('click', lambda: update_styles('True'))
                                    
                                    update_styles('False') # Apply initial style

                                # Advanced Settings Expansion
                                with ui.expansion('Advanced Analysis Options', icon='settings').classes('w-full').style('background: rgba(255,255,255,0.1); border-radius: 0.75rem; color: white; margin-top: 1rem;'):
                                    with ui.element('div').style('display: flex; flex-direction: column; gap: 1.5rem; text-align: left; padding: 1rem;'):
                                        # Bootstrap Samples
                                        with ui.element('div'):
                                            with ui.row().style('display: flex; align-items: center; gap: 0.5rem;'):
                                                ui.label('Bootstrap Samples (B)').style('color: #fff; font-weight: 600; font-size: 0.95rem;')
                                                with ui.tooltip('Number of bootstrap samples for uncertainty estimation. Higher values increase precision but take longer.').style('background: var(--primary-800); color: white;'):
                                                    ui.icon('help_outline', size='xs').style('cursor: help;')
                                            with ui.element('div').style('background: rgba(255,255,255,0.9); border-radius: 0.5rem; padding: 0.5rem;'):
                                                B_input = ui.number('', value=2000, min=50, max=5000, step=50).style('width: 100%; border: none; background: transparent; color: #011f5b; font-weight: 500;')

                                        # Random Seed
                                        with ui.element('div'):
                                            with ui.row().style('display: flex; align-items: center; gap: 0.5rem;'):
                                                ui.label('Reproducibility Seed').style('color: #fff; font-weight: 600; font-size: 0.95rem;')
                                                with ui.tooltip('Set a fixed number to ensure results are perfectly reproducible. Leave blank for random results.').style('background: var(--primary-800); color: white;'):
                                                    ui.icon('help_outline', size='xs').style('cursor: help;')
                                            with ui.element('div').style('background: rgba(255,255,255,0.9); border-radius: 0.5rem; padding: 0.5rem;'):
                                                seed_input = ui.number('', value=1, min=1, max=999999, step=1).style('width: 100%; border: none; background: transparent; color: #011f5b; font-weight: 500;')

                # Default values for hidden parameters (if needed)
                B_input_default = 2000
                seed_input_default = 1

                # Generate button
                with ui.element('div').style('display: flex; justify-content: center; margin-top: 3.5rem;'):
                    query_button = ui.button('', icon='rocket_launch').classes('primary-btn').style('padding: 1.25rem 3rem; font-size: 1.1rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; border-radius: 2rem; box-shadow: 0 6px 24px rgba(1,31,91,0.18);')
                    with query_button:
                        ui.html('<span style="font-weight: 800; font-size: 1.1rem;">Generate Report</span>')

        # Status and Report containers are now initialized globally for both modes
    
        async def on_query():
            """Create ranking job, poll status, then fetch and render results."""
            try:
                # Clear previous content and show enhanced loading status
                report_container.clear()
                status_container.clear()
                # Make containers visible
                status_container.style('display: block;')
                report_container.style('display: none;')
                
                # Enhanced loading animation
                with status_container:
                    with ui.element('div').classes('status-card').style('''
                        background: linear-gradient(135deg, rgba(1, 31, 91, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%);
                        border: 1px solid rgba(1, 31, 91, 0.1);
                        backdrop-filter: blur(15px);
                    '''):
                        ui.html('''
                            <div style="display: flex; align-items: center; gap: 1.5rem; justify-content: center;">
                                <div class="loading-spinner"></div>
                                <div style="color: var(--primary-900); font-weight: 700; font-size: 1.1rem;">
                                    🔍 Performing robust ranking analysis...
                                </div>
                            </div>
                            <div style="margin-top: 1rem; text-align: center; color: var(--gray-600); font-size: 0.9rem;">
                                Please wait while we process your report
                            </div>
                        ''')
                
                # Validate input file
                if not uploaded_state['content']:
                    ui.notify('🚨 Please upload a CSV file', type='negative')
                    status_container.clear()
                    return

                file_name = uploaded_state['name'] or 'data.csv'
                file_bytes = uploaded_state['content']

                # Use values from inputs if they exist, otherwise use defaults
                b_value = int(B_input.value) if 'B_input' in locals() and B_input.value is not None else B_input_default
                seed_value = int(seed_input.value) if 'seed_input' in locals() and seed_input.value is not None else seed_input_default

                # Create job
                job_id, err = await create_job_async(file_name, file_bytes, (ranking_direction_state['value'] == 'True'), b_value, seed_value)
                if err or not job_id:
                    logger.error(f"Create job failed: {err}")
                    ui.notify(f'🚨 Analysis Failed: {err}', type='negative')
                    with status_container:
                        with ui.element('div').classes('status-card info-card error').style('''
                            background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
                            border-left: 5px solid var(--error-500);
                        '''):
                            ui.html(f'''
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <div style="font-size: 1.5rem;">❌</div>
                                    <div>
                                        <div style="color: var(--error-600); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
                                            Analysis Failed
                                        </div>
                                        <div style="color: var(--gray-700); font-size: 0.95rem;">
                                            {err or 'Job creation failed'}
                                        </div>
                                    </div>
                                </div>
                            ''')
                    return

                # Poll status
                status = await poll_status_async(job_id)
                if status.get('status') != 'succeeded':
                    ui.notify(f'🚨 Analysis Failed: {status.get("message","Unknown error")}', type='negative')
                    return

                # Fetch results
                result, err = await fetch_results_async(job_id)
                if err or not result:
                    ui.notify(f'🚨 Fetch Results Failed: {err}', type='negative')
                    return

                status_container.clear()
                status_container.style('display: none;')
                report_container.style('display: block;')

                with status_container:
                        with ui.element('div').classes('status-card info-card phewas').style('''
                            background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
                            border-left: 5px solid var(--accent-500);
                        '''):
                            ui.html('''
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <div style="font-size: 1.5rem;">✅</div>
                                    <div>
                                        <div style="color: var(--accent-600); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
                                            Analysis Complete
                                        </div>
                                        <div style="color: var(--gray-700); font-size: 0.95rem;">
                                        Your ranking report has been generated successfully
                                        </div>
                                    </div>
                                </div>
                            ''')

                with report_container:
                    show_results(result)
                        
            except Exception as e:
                error_msg = f"Unexpected system error: {str(e)}"
                logger.error(error_msg)
                ui.notify(f'🚨 System Error: {error_msg}', type='negative')
                status_container.clear()
                with status_container:
                    with ui.element('div').classes('status-card info-card error'):
                        ui.html(f'''
                            <div style="display: flex; align-items: center; gap: 1rem;">
                                <div style="font-size: 1.5rem;">💥</div>
                                <div>
                                    <div style="color: var(--error-600); font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem;">
                                        System Error
                                    </div>
                                    <div style="color: var(--gray-700); font-size: 0.95rem;">
                                        {error_msg}
                                    </div>
                                </div>
                            </div>
                        ''')
    
        # Use the enhanced async handler for the button click
        query_button.on('click', on_query)
        
        # Shared Status and Report Containers (used by both agent and manual modes)
        # Placed after analysis sections but before documentation for proper layout
        status_container = ui.element('div').props('id="status-container"').style('max-width: 1400px; margin: 0 auto; width: 100%; position: relative; z-index: 10; display: none;')
        report_container = ui.column().classes('w-full').style('max-width: 1200px; margin: 0 auto; position: relative; background: white; border-radius: var(--radius-2xl); padding: 2rem; margin-bottom: 0; box-shadow: var(--shadow-md); display: none;').props('id="results"')

        # Bind global refs for reuse across modes
        try:
            report_container_ref = report_container
            status_container_ref = status_container
        except Exception:
            pass

    # Documentation & Help section moved here, margin removed for tight spacing
    with ui.element('section').style('width: 100%; max-width: 1400px; margin: 1rem auto; padding: 0;').props('id="documentation"'):
        with ui.element('div').classes('info-card').style('text-align: center; margin-bottom: 0.5rem; border: 3px solid #011f5b;'):
            ui.html('''
                <div style="margin-bottom: 0rem;">
                    <div style="display: flex; align-items: center; justify-content: center; gap: 1rem; margin-bottom: 1.5rem;">
                        <span class="material-symbols-outlined" style="font-size: 2rem;">menu_book</span>
                        <h2 style="color: var(--primary-900); font-weight: 800; margin: 0; font-size: 1.5rem;">How to Use This Tool</h2>
                    </div>
                    <p style="color: var(--gray-600); font-size: 0.9rem; max-width: 600px; margin: 0 auto;">
                        Follow these simple steps to generate your robust ranking report.
                    </p>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem; margin-top: 1.5rem;">
                    <div class="highlight-box" style="text-align: left; background: #011f5b; color: #fff;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #fff; text-align: center;">
                            <span class="material-symbols-outlined" style="font-size: 1.5rem;">counter_1</span>
                            <h4 style="color: #fff; margin: 0; font-weight: 800; font-size: 1.1rem; display: inline-block;"><b>Upload Data</b></h4>
                        </div>
                        <p style="color: #fff;">Upload a CSV file where rows represent samples and columns represent the methods to be ranked.</p>
                    </div>
                    <div class="highlight-box" style="text-align: left; background: #011f5b; color: #fff;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #fff; text-align: center;">
                            <span class="material-symbols-outlined" style="font-size: 1.5rem;">counter_2</span>
                            <h4 style="color: #fff; margin: 0; font-weight: 800; font-size: 1.1rem; display: inline-block;"><b>Set Parameters</b></h4>
                        </div>
                        <p style="color: #fff;">Specify whether higher or lower values indicate better performance. Adjust advanced settings if needed.</p>
                    </div>
                    <div class="highlight-box" style="text-align: left; background: #011f5b; color: #fff;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #fff; text-align: center;">
                            <span class="material-symbols-outlined" style="font-size: 1.5rem;">counter_3</span>
                            <h4 style="color: #fff; margin: 0; font-weight: 800; font-size: 1.1rem; display: inline-block;"><b>Generate Report</b></h4>
                        </div>
                        <p style="color: #fff;">Click the "Generate Report" button to receive your ranking analysis with confidence intervals.</p>
                    </div>
                </div>
            ''')

    # About PRSAgent section moved here, margin removed for tight spacing
    with ui.element('section').style('width: 100%; max-width: 1400px; margin: 1rem auto 4rem auto; padding: 0;').props('id="about"'):
        with ui.element('div').classes('info-card').style('text-align: center; margin-bottom: 0.5rem; border: 3px solid #011f5b;'):
            ui.html('''
                <div style="margin-bottom: 0rem;">
                    <div style="display: flex; align-items: center; justify-content: center; gap: 1rem; margin-bottom: 1.5rem;">
                        <span class="material-symbols-outlined" style="font-size: 2rem;">lightbulb</span>
                        <h2 style="color: var(--primary-900); font-weight: 800; margin: 0; font-size: 1.5rem;">About This Framework</h2>
                    </div>
                    <p style="color: var(--gray-600); font-size: 0.9rem; max-width: 800px; margin: 0 auto; line-height: 1.6;">
                        This tool implements a statistical framework for robustly ranking entities based on varied comparisons. It excels in handling heterogeneous data where items are compared in groups of different sizes, a common scenario in real-world applications.<br>The core of our approach is the <strong>Spectral Method</strong>, which estimates underlying preference scores, combined with a <strong>Weighted Bootstrap</strong> to quantify the uncertainty of the resulting ranks.
                    </p>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 2rem; margin-top: 1.5rem;">
                    <div class="highlight-box" style="text-align: center; background: #011f5b; color: #fff;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #fff;">
                            <span class="material-symbols-outlined" style="font-size: 1.5rem;">target</span>
                            <h4 style="color: #fff; margin: 0; font-weight: 800; font-size: 1.1rem;"><b>General Fixed Graph</b></h4>
                        </div>
                        <p style="color: #fff;">Circumvents restrictive assumptions, allowing for flexible, real-world comparison structures.</p>
                    </div>
                    <div class="highlight-box" style="text-align: center; background: #011f5b; color: #fff;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #fff;">
                            <span class="material-symbols-outlined" style="font-size: 1.5rem;">science</span>
                            <h4 style="color: #fff; margin: 0; font-weight: 800; font-size: 1.1rem;"><b>Asymptotic Efficiency</b></h4>
                        </div>
                        <p style="color: #fff;">Our two-step spectral method can achieve the same asymptotic efficiency as the MLE.</p>
                    </div>
                    <div class="highlight-box" style="text-align: center; background: #011f5b; color: #fff;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #fff;">
                            <span class="material-symbols-outlined" style="font-size: 1.5rem;">analytics</span>
                            <h4 style="color: #fff; margin: 0; font-weight: 800; font-size: 1.1rem;"><b>Ranking Inferences</b></h4>
                        </div>
                        <p style="color: #fff;">Provides a comprehensive framework for both one-sample and two-sample ranking inferences.</p>
                    </div>
                    <div class="highlight-box" style="text-align: center; background: #011f5b; color: #fff;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #fff;">
                            <span class="material-symbols-outlined" style="font-size: 1.5rem;">verified</span>
                            <h4 style="color: #fff; margin: 0; font-weight: 800; font-size: 1.1rem;"><b>Proven Methodology</b></h4>
                        </div>
                        <p style="color: #fff;">Validated through comprehensive simulations and applied to real-world datasets.</p>
                    </div>
                </div>
            ''')

    # Footer
    with ui.element('footer').classes('footer-section').style('margin: 0 -1rem; width: calc(100% + 2rem); background: linear-gradient(135deg, #1e3a8a 0%, #011f5b 40%, #000d26 80%, #00071a 100%); color: white; padding: 3rem 2rem 2rem; position: relative; overflow: hidden;'):
        # Add footer deep sea effects CSS
        ui.add_head_html('''
        <style>
        .footer-section {
          position: relative;
          overflow: hidden;
        }

        .footer-section::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background:
            radial-gradient(circle at 20% 30%, rgba(1, 31, 91, 0.3) 0%, transparent 50%),
            radial-gradient(circle at 80% 70%, rgba(0, 17, 51, 0.4) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, rgba(0, 10, 26, 0.2) 0%, transparent 60%);
          pointer-events: none;
          z-index: 0;
        }

        .footer-section::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: linear-gradient(45deg, transparent 40%, rgba(255, 255, 255, 0.02) 50%, transparent 60%);
          animation: waterShimmer 8s ease-in-out infinite;
          pointer-events: none;
          z-index: 0;
        }

        .footer-floating-particles {
          display: block !important;
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          overflow: hidden;
          z-index: 0;
          pointer-events: none;
        }

        .footer-floating-particles .particle {
          position: absolute;
          bottom: -100px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.5);
          animation: float 25s infinite linear;
          opacity: 0;
        }

        .footer-floating-particles .particle:nth-child(1) { width: 4px; height: 4px; left: 10%; animation-duration: 20s; animation-delay: 0s; }
        .footer-floating-particles .particle:nth-child(2) { width: 2px; height: 2px; left: 25%; animation-duration: 30s; animation-delay: -5s; }
        .footer-floating-particles .particle:nth-child(3) { width: 5px; height: 5px; left: 40%; animation-duration: 15s; animation-delay: -10s; }
        .footer-floating-particles .particle:nth-child(4) { width: 3px; height: 3px; left: 55%; animation-duration: 22s; animation-delay: -1s; }
        .footer-floating-particles .particle:nth-child(5) { width: 2px; height: 2px; left: 70%; animation-duration: 28s; animation-delay: -15s; }
        .footer-floating-particles .particle:nth-child(6) { width: 4px; height: 4px; left: 85%; animation-duration: 18s; animation-delay: -8s; }
        .footer-floating-particles .particle:nth-child(7) { width: 3px; height: 3px; left: 5%; animation-duration: 26s; animation-delay: -4s; }
        .footer-floating-particles .particle:nth-child(8) { width: 2px; height: 2px; left: 95%; animation-duration: 32s; animation-delay: -18s; }
        .footer-floating-particles .particle:nth-child(9) { width: 5px; height: 5px; left: 50%; animation-duration: 14s; animation-delay: -20s; }
        .footer-floating-particles .particle:nth-child(10) { width: 3px; height: 3px; left: 15%; animation-duration: 24s; animation-delay: -2s; }
        .footer-floating-particles .particle:nth-child(11) { width: 4px; height: 4px; left: 30%; animation-duration: 19s; animation-delay: -7s; }
        .footer-floating-particles .particle:nth-child(12) { width: 2px; height: 2px; left: 45%; animation-duration: 27s; animation-delay: -12s; }
        .footer-floating-particles .particle:nth-child(13) { width: 5px; height: 5px; left: 60%; animation-duration: 16s; animation-delay: -3s; }
        .footer-floating-particles .particle:nth-child(14) { width: 3px; height: 3px; left: 75%; animation-duration: 21s; animation-delay: -9s; }
        .footer-floating-particles .particle:nth-child(15) { width: 2px; height: 2px; left: 90%; animation-duration: 29s; animation-delay: -14s; }
        .footer-floating-particles .particle:nth-child(16) { width: 4px; height: 4px; left: 20%; animation-duration: 23s; animation-delay: -6s; }
        .footer-floating-particles .particle:nth-child(17) { width: 3px; height: 3px; left: 35%; animation-duration: 17s; animation-delay: -11s; }
        .footer-floating-particles .particle:nth-child(18) { width: 5px; height: 5px; left: 80%; animation-duration: 25s; animation-delay: -16s; }
        .footer-floating-particles .particle:nth-child(19) { width: 4px; height: 4px; left: 8%; animation-duration: 22s; animation-delay: -4s; }
        .footer-floating-particles .particle:nth-child(20) { width: 2px; height: 2px; left: 18%; animation-duration: 31s; animation-delay: -8s; }
        .footer-floating-particles .particle:nth-child(21) { width: 3px; height: 3px; left: 28%; animation-duration: 18s; animation-delay: -13s; }
        .footer-floating-particles .particle:nth-child(22) { width: 5px; height: 5px; left: 38%; animation-duration: 26s; animation-delay: -5s; }
        .footer-floating-particles .particle:nth-child(23) { width: 4px; height: 4px; left: 48%; animation-duration: 20s; animation-delay: -10s; }
        .footer-floating-particles .particle:nth-child(24) { width: 2px; height: 2px; left: 58%; animation-duration: 28s; animation-delay: -15s; }
        .footer-floating-particles .particle:nth-child(25) { width: 3px; height: 3px; left: 68%; animation-duration: 17s; animation-delay: -7s; }
        .footer-floating-particles .particle:nth-child(26) { width: 5px; height: 5px; left: 78%; animation-duration: 24s; animation-delay: -12s; }
        .footer-floating-particles .particle:nth-child(27) { width: 4px; height: 4px; left: 88%; animation-duration: 19s; animation-delay: -9s; }
        .footer-floating-particles .particle:nth-child(28) { width: 2px; height: 2px; left: 12%; animation-duration: 30s; animation-delay: -14s; }
        .footer-floating-particles .particle:nth-child(29) { width: 3px; height: 3px; left: 22%; animation-duration: 16s; animation-delay: -6s; }
        .footer-floating-particles .particle:nth-child(30) { width: 5px; height: 5px; left: 32%; animation-duration: 23s; animation-delay: -11s; }
        .footer-floating-particles .particle:nth-child(31) { width: 4px; height: 4px; left: 42%; animation-duration: 21s; animation-delay: -8s; }
        .footer-floating-particles .particle:nth-child(32) { width: 2px; height: 2px; left: 52%; animation-duration: 27s; animation-delay: -13s; }
        .footer-floating-particles .particle:nth-child(33) { width: 3px; height: 3px; left: 62%; animation-duration: 18s; animation-delay: -5s; }
        .footer-floating-particles .particle:nth-child(34) { width: 5px; height: 5px; left: 72%; animation-duration: 25s; animation-delay: -10s; }
        .footer-floating-particles .particle:nth-child(35) { width: 4px; height: 4px; left: 82%; animation-duration: 20s; animation-delay: -15s; }
        .footer-floating-particles .particle:nth-child(36) { width: 2px; height: 2px; left: 92%; animation-duration: 29s; animation-delay: -7s; }
        .footer-floating-particles .particle:nth-child(37) { width: 3px; height: 3px; left: 6%; animation-duration: 22s; animation-delay: -12s; }
        .footer-floating-particles .particle:nth-child(38) { width: 5px; height: 5px; left: 16%; animation-duration: 17s; animation-delay: -9s; }
        .footer-floating-particles .particle:nth-child(39) { width: 4px; height: 4px; left: 26%; animation-duration: 24s; animation-delay: -14s; }
        .footer-floating-particles .particle:nth-child(40) { width: 2px; height: 2px; left: 36%; animation-duration: 19s; animation-delay: -6s; }
        .footer-floating-particles .particle:nth-child(41) { width: 3px; height: 3px; left: 46%; animation-duration: 26s; animation-delay: -11s; }
        .footer-floating-particles .particle:nth-child(42) { width: 5px; height: 5px; left: 56%; animation-duration: 21s; animation-delay: -8s; }
        .footer-floating-particles .particle:nth-child(43) { width: 4px; height: 4px; left: 66%; animation-duration: 28s; animation-delay: -13s; }
        .footer-floating-particles .particle:nth-child(44) { width: 2px; height: 2px; left: 76%; animation-duration: 18s; animation-delay: -5s; }
        .footer-floating-particles .particle:nth-child(45) { width: 3px; height: 3px; left: 86%; animation-duration: 23s; animation-delay: -10s; }
        .footer-floating-particles .particle:nth-child(46) { width: 5px; height: 5px; left: 96%; animation-duration: 20s; animation-delay: -15s; }
        .footer-floating-particles .particle:nth-child(47) { width: 4px; height: 4px; left: 2%; animation-duration: 25s; animation-delay: -7s; }
        .footer-floating-particles .particle:nth-child(48) { width: 2px; height: 2px; left: 98%; animation-duration: 16s; animation-delay: -12s; }

        </style>
        ''')

        # Add footer particles
        with ui.element('div').classes('footer-floating-particles'):
            # Add 48 particles for footer to match hero section
            for i in range(48):
                ui.element('div').classes('particle')

        with ui.element('div').style('width: 100%; padding: 0 2rem; text-align: center; position: relative; z-index: 1;'):
            ui.html('''
                <div style="display: flex; align-items: center; justify-content: center; gap: 1rem; margin-bottom: 2rem;">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/7/7c/Shield_of_the_University_of_Pennsylvania.svg" alt="UPenn Shield" style="height: 2.5rem; width: auto; display: block; margin: 0; padding: 0;"/>
                    <span style="font-weight: 900; font-size: 1.5rem;">  Robust Spectral Ranking</span>
                    <img src="https://static.cdnlogo.com/logos/w/18/washington-university-in-st-louis.svg" alt="WUSTL Shield" style="height: 3.2rem; width: auto; display: block; margin: 0; padding: 0;"/>
                </div>
                <p style="opacity: 0.8; margin-bottom: 1rem;">
                    A Robust Statistical Framework for Ranking and Uncertainty Quantification.
                </p>
                <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin-top: 2rem; margin-bottom: 2rem;">
                    <div style="text-align: center;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                            <img src="https://arxiv.org/static/browse/0.3.4/images/arxiv-logo-one-color-white.svg" alt="arXiv" style="height: 1.5rem; width: auto; display: block; margin: 0; padding: 0;"/>
                            <h4 style="color: white; margin: 0;">Based on Published Research</h4>
                        </div>
                        <a href="https://doi.org/10.1287/opre.2023.0439" target="_blank" style="color: var(--primary-700); text-decoration: none; font-weight: 500;">doi.org/10.1287/opre.2023.0439</a>
                    </div>
                    <div style="text-align: center;">
                        <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                            <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/github/github-original.svg" alt="GitHub" style="height: 1.5rem; width: auto; display: block; margin: 0; padding: 0; filter: brightness(0) invert(1);"/>
                            <h4 style="color: white; margin: 0;">Source Code</h4>
                        </div>
                        <a href="https://github.com/MaxineYu/Spectral_Ranking" target="_blank" style="color: var(--primary-700); text-decoration: none; font-weight: 500;">GitHub Repository</a>
                    </div>
                </div>
                <p style="opacity: 0.6; font-size: 0.9rem;">
                    © 2024 Robust Spectral Ranking Framework | University of Pennsylvania & Washington University in St. Louis
                </p>
            ''')

# Enhanced UI configuration with modern theme
ui.run(
    title='Spectral Ranking',
    reload=True,
    dark=False,
    port=int(os.getenv('PORT', 8080)),
    host='0.0.0.0',
    favicon='Σ',
    show=True
)
# kill -9 $(lsof -ti :8001)
# kill -9 $(lsof -ti :8080)
# conda activate PRSAgent && uvicorn code_app.backend.main:app --host 0.0.0.0 --port 8001
# conda activate PRSAgent && python code_app/frontend/main.py
# conda activate PRSAgent && python code_app/frontend/main.py
