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

# Client-specific state storage - each client has isolated state
_client_states = {}

def get_client_id():
    """Get the current client ID for state isolation"""
    try:
        return ui.context.client.id
    except:
        # Fallback for cases where context is not available
        return 'default'

def get_client_state():
    """Get or initialize client-specific state"""
    client_id = get_client_id()
    if client_id not in _client_states:
        _client_states[client_id] = {
            'api_key_confirmed': False,
            'current_mode': 'agent',
            'current_agent_file_id': None,
            'current_agent_job_id': None,
            '_analysis_completed': False,
            'agent_conversation_history': [],
            'agent_context': {
                'conversation_history': [],
                'current_stage': 'awaiting_upload',
                'user_preferences': {},
                'data_insights': {},
                'last_activity': None
            },
            'manual_uploaded_file': None,
            'chat_state': {
                'messages': [{'role': 'assistant', 'content': 'Welcome to SpectralRank! I\'m SpectralRank Agent — here to help you navigate and use this platform. I can answer questions, perform ranking analysis, and analyze results. Let me know what you need help with!'}],
                'uploaded_file_id': None,
                'current_job_id': None
            }
        }
    return _client_states[client_id]

# Global references to agent chat components (these are UI elements, not state)
global_messages_container = None
global_input_field = None
global_api_key_input = None
global_confirm_button = None


def set_global_confirm_button(button):
    """Store confirm button reference for later UI reset."""
    global global_confirm_button
    global_confirm_button = button

# Global flag to ensure status panel CSS is only added once
_status_panel_css_added = False

# Dashboard route
@ui.page('/dashboard')
def dashboard_page():
    """Dashboard page for LLM performance visualization"""
    # Initialize API base URL for dashboard page
    ui.add_head_html(f'''
    <script>
    window.apiBaseUrl = window.apiBaseUrl || '{API_BASE_URL}';

    // Ensure textarea text starts from top and initialize attachment button
    document.addEventListener('DOMContentLoaded', function() {{
        setTimeout(function() {{
            const textareas = document.querySelectorAll('.top-aligned-textarea textarea');
            textareas.forEach(function(textarea) {{
                textarea.style.paddingTop = '0px';
                textarea.style.marginTop = '0px';
                textarea.style.verticalAlign = 'top';
                textarea.scrollTop = 0;
            }});

            // Initialize attachment button state - check if file is already uploaded
            const attachmentBtn = document.getElementById('attachment-button');
            const uploadArea = document.getElementById('agent-upload-area');
            if (attachmentBtn) {{
                // Check if upload area shows uploaded state
                if (uploadArea && uploadArea.classList.contains('uploaded')) {{
                    // File already uploaded, disable button
                    attachmentBtn.classList.add('disabled');
                    attachmentBtn.disabled = true;
                }} else {{
                    // No file uploaded, enable button
                    attachmentBtn.classList.remove('disabled');
                    attachmentBtn.disabled = false;
                }}
            }}

            // Force message input textarea to use full width and proper height
            function fixMessageInputWidth() {{
                const messageInput = document.getElementById('message-input');
                if (messageInput) {{
                    // Set textarea styles directly - force full width
                    messageInput.style.setProperty('width', '100%', 'important');
                    messageInput.style.setProperty('max-width', '100%', 'important');
                    messageInput.style.setProperty('box-sizing', 'border-box', 'important');
                    messageInput.style.setProperty('min-width', '0', 'important');
                    messageInput.style.setProperty('display', 'block', 'important');
                    messageInput.style.setProperty('white-space', 'pre-wrap', 'important');
                    messageInput.style.setProperty('word-wrap', 'break-word', 'important');
                    messageInput.style.setProperty('overflow-wrap', 'break-word', 'important');
                    messageInput.style.setProperty('word-break', 'break-word', 'important');
                    
                    // Set height properties
                    messageInput.style.setProperty('height', 'auto', 'important');
                    messageInput.style.setProperty('min-height', '2.5rem', 'important');
                    messageInput.style.setProperty('max-height', '10rem', 'important');
                    messageInput.style.setProperty('overflow-y', 'auto', 'important');
                    messageInput.style.setProperty('overflow-x', 'hidden', 'important');
                    messageInput.style.setProperty('padding', '0.5rem 0.25rem', 'important');
                    
                    // Auto-adjust height based on content
                    function adjustHeight() {{
                        messageInput.style.height = 'auto';
                        const scrollHeight = messageInput.scrollHeight;
                        const rootFontSize = parseFloat(getComputedStyle(document.documentElement).fontSize);
                        const maxHeight = 10 * rootFontSize; // 10rem in pixels
                        const minHeight = 2.5 * rootFontSize; // 2.5rem in pixels
                        const newHeight = Math.max(minHeight, Math.min(scrollHeight, maxHeight));
                        messageInput.style.height = newHeight + 'px';
                    }}
                    
                    // Adjust height on input
                    if (!messageInput.hasAttribute('data-height-listener')) {{
                        messageInput.addEventListener('input', adjustHeight);
                        messageInput.setAttribute('data-height-listener', 'true');
                    }}
                    
                    // Initial height adjustment - use multiple timeouts to ensure DOM is ready
                    setTimeout(function() {{
                        adjustHeight();
                    }}, 0);
                    
                    setTimeout(function() {{
                        adjustHeight();
                    }}, 100);
                    
                    setTimeout(function() {{
                        adjustHeight();
                    }}, 500);
                    
                    // Also adjust when textarea becomes visible
                    const visibilityObserver = new IntersectionObserver(function(entries) {{
                        entries.forEach(function(entry) {{
                            if (entry.isIntersecting) {{
                                adjustHeight();
                            }}
                        }});
                    }}, {{ threshold: 0.1 }});
                    
                    visibilityObserver.observe(messageInput);
                    
                    // Ensure all parent containers use full width
                    let current = messageInput.parentElement;
                    let depth = 0;
                    while (current && depth < 5) {{
                        const style = window.getComputedStyle(current);
                        current.style.setProperty('width', '100%', 'important');
                        current.style.setProperty('min-width', '0', 'important');
                        current.style.setProperty('box-sizing', 'border-box', 'important');
                        current.style.setProperty('overflow', 'visible', 'important');
                        
                        if (style.display === 'flex' || style.display === 'block') {{
                            if (style.display === 'flex') {{
                                if (current.style.flex === '' || current.style.flex === 'none' || !current.style.flex) {{
                                    current.style.setProperty('flex', '1 1 0%', 'important');
                                }}
                            }} else {{
                                current.style.setProperty('display', 'block', 'important');
                            }}
                        }}
                        current = current.parentElement;
                        depth++;
                    }}
                }}
            }}
            
            // Fix width on load and when input area becomes visible
            fixMessageInputWidth();
            
            // Fix on window resize
            window.addEventListener('resize', function() {{
                setTimeout(fixMessageInputWidth, 50);
            }});
            
            // Also fix when switching to agent mode or when DOM changes
            const observer = new MutationObserver(function(mutations) {{
                setTimeout(fixMessageInputWidth, 50);
            }});
            
            const agentSection = document.getElementById('agent-analysis');
            if (agentSection) {{
                observer.observe(agentSection, {{ 
                    attributes: true, 
                    attributeFilter: ['style'],
                    childList: true,
                    subtree: true
                }});
            }}
            
            // Also observe the input field itself
            const messageInput = document.getElementById('message-input');
            if (messageInput) {{
                observer.observe(messageInput, {{
                    attributes: true,
                    attributeFilter: ['style']
                }});
            }}
        }}, 100);
    }});
    </script>
    ''')
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
  gap: 1rem;
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

.top-aligned-textarea textarea {
  padding-top: 0 !important;
  margin-top: 0 !important;
  line-height: 1.2 !important;
  vertical-align: top !important;
}

.top-aligned-textarea textarea::placeholder {
  position: relative;
  top: 0;
  transform: none !important;
}

.attachment-btn.disabled {
  background: rgba(255, 255, 255, 0.3) !important;
  border-color: rgba(1, 31, 91, 0.2) !important;
  color: rgba(1, 31, 91, 0.3) !important;
  cursor: not-allowed !important;
  opacity: 0.08 !important;
  filter: grayscale(100%) !important;
  transform: scale(0.9) !important;
  box-shadow: none !important;
}

.attachment-btn.disabled .material-symbols-outlined {
  color: var(--gray-600) !important;
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
  /* Make scrollbar overlay content without taking up space */
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;
}

body:hover, html:hover {
  scrollbar-color: rgba(156, 163, 175, 0.7) rgba(243, 244, 246, 0.5);
}

body.scrolling {
  scrollbar-color: rgba(156, 163, 175, 0.7) rgba(243, 244, 246, 0.5);
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
  max-width: 1000px;
  margin: 0 auto 2.5rem;
  line-height: 1.7;
  position: relative;
  animation: fadeInUp 0.8s ease-out 0.4s both;
  text-shadow: none;
  color: #e5e7eb;
  width: 100%;
}

.hero-features {
  display: flex;
  flex-wrap: nowrap;
  gap: 1.5rem;
  max-width: 1200px;
  margin: 2.5rem auto 0;
  animation: fadeInUp 0.8s ease-out 0.6s both;
  justify-content: center;
}

.hero-feature {
  background: #fff;
  border: 1.5px solid #011f5b;
  border-radius: var(--radius-xl);
  padding: 1.2rem 1.2rem 1rem 1.2rem;
  text-align: center;
  transition: var(--transition-slow);
  box-shadow: 0 2px 8px rgba(1,31,91,0.07);
  min-width: 280px;
  max-width: 300px;
  width: 280px;
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: #011f5b;
}

.hero-feature:hover {
  transform: translateY(-4px);
  background: #f3f4f6;
  box-shadow: 0 4px 16px rgba(1,31,91,0.12);
}

/* Example Data Cards */
.example-data-card {
  box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1);
}

.example-data-card:hover {
  transform: translateY(-4px) scale(1.02);
  border-color: rgba(59,130,246,0.4);
  box-shadow: 0 8px 25px rgba(0,0,0,0.15), 0 4px 10px rgba(0,0,0,0.1);
}

.example-data-card:hover img {
  transform: scale(1.1);
  filter: brightness(1.2);
}

.example-data-card:hover > div:first-child {
  opacity: 1;
}

.example-data-card-aou:hover {
  border-color: rgba(59,130,246,0.6);
}

.example-data-card-ukbb:hover {
  border-color: rgba(16,185,129,0.6);
}

.hero-feature-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  display: block;
  opacity: 1;
  animation: none;
  color: #011f5b !important;
}

.hero-feature-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.4rem;
  color: #011f5b;
  white-space: nowrap;
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

  .example-data-cards {
    grid-template-columns: 1fr !important;
    gap: 1rem !important;
  }

  .example-data-card {
    padding: 1rem !important;
  }

  .example-data-card:hover {
    transform: translateY(-2px) scale(1.01) !important;
  }

  .example-data-card img {
    width: 2.5rem !important;
    height: 2.5rem !important;
    object-fit: contain !important;
    margin: 0 auto 0.75rem auto !important;
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
  font-size: 0.8rem;
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
  border-bottom: 1px solid rgba(1, 31, 91, 0.1);
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
  box-shadow: var(--shadow-lg);
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 700;
  font-size: 1.25rem;
}

.navbar-brand-link {
  text-decoration: none;
  color: var(--primary-900) !important;
  font-weight: 700;
  font-size: 1.25rem;
  transition: var(--transition-base);
  cursor: pointer;
}

.navbar-brand-link:hover {
  color: var(--primary-900) !important;
  opacity: 0.8;
  transform: translateY(-1px);
  text-decoration: none;
}

.navbar-brand-icon {
  font-size: 1.5rem;
  color: var(--primary-900);
}

.navbar-nav {
  display: flex;
  align-items: center;
  gap: 1rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-item {
  position: relative;
}

.nav-link {
  color: rgba(1, 31, 91, 0.8);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  transition: var(--transition-base);
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 50%;
  width: 0;
  height: 2px;
  background: var(--primary-900);
  transition: var(--transition-base);
  transform: translateX(-50%);
}

.nav-link:hover {
  color: var(--primary-900);
  background: rgba(1, 31, 91, 0.1);
  transform: translateY(-1px);
}

.nav-link:hover::after {
  width: 100%;
}

.nav-link.active {
  color: var(--primary-900);
  background: rgba(1, 31, 91, 0.15);
}

.nav-link.active::after {
  width: 100%;
  background: var(--primary-900);
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.nav-button {
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

.nav-button:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.nav-button.primary {
  background: rgba(1, 31, 91, 0.1);
  color: var(--primary-900);
  border: 1px solid rgba(1, 31, 91, 0.2);
}

.nav-button.primary:hover {
  background: rgba(1, 31, 91, 0.2);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

/* Mobile Navigation */
.mobile-toggle {
  display: none;
  background: none;
  border: none;
  color: var(--primary-900);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: var(--radius-md);
  transition: var(--transition-base);
}

.mobile-toggle:hover {
  background: rgba(1, 31, 91, 0.1);
}

.mobile-nav {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(1, 31, 91, 0.1);
  padding: 1rem 2rem;
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
    font-size: 0.8rem;
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
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
  border-radius: var(--radius-sm);
  transition: background 0.3s ease;
}

::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: var(--radius-sm);
  transition: background 0.3s ease;
}

/* Show scrollbar when body is hovered or scrolling */
body:hover ::-webkit-scrollbar-thumb,
body.scrolling ::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.7);
}

body:hover ::-webkit-scrollbar-track,
body.scrolling ::-webkit-scrollbar-track {
  background: rgba(243, 244, 246, 0.5);
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.85);
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

#agent-upload-area.uploaded, #manual-upload-area.uploaded, #shared-upload-area.uploaded {
  border-color: #6b7280 !important;
  background: rgba(107, 114, 128, 0.1) !important;
  cursor: default !important;
}

#agent-upload-area.uploaded #agent-upload-content,
#manual-upload-area.uploaded #manual-upload-content,
#shared-upload-area.uploaded #shared-upload-content {
  background: rgba(107, 114, 128, 0.1) !important;
}

/* Delete Button Styling */
.upload-delete-btn {
  background: transparent !important;
  color: var(--gray-500) !important;
  border: none !important;
  border-radius: var(--radius-sm) !important;
  width: 24px !important;
  height: 24px !important;
  cursor: pointer !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 1.2rem !important;
  transition: all 0.2s ease !important;
  position: relative !important;
  z-index: 20 !important;
}

.upload-delete-btn:hover {
  background: rgba(239, 68, 68, 0.1) !important;
  color: var(--error-500) !important;
  transform: scale(1.1) !important;
}

/* Chat Messages Container Styling - Ultra Transparent Scrollbar */
.chat-messages {
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.05) transparent;
}

.chat-messages::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.08);
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

/* Table scroll container styling */
.data-preview-table-scroll {
  scrollbar-width: thin;
  scrollbar-color: var(--primary-900) var(--gray-200);
}

.data-preview-table-scroll::-webkit-scrollbar {
  height: 8px;
}

.data-preview-table-scroll::-webkit-scrollbar-track {
  background: var(--gray-100);
  border-radius: var(--radius-sm);
}

.data-preview-table-scroll::-webkit-scrollbar-thumb {
  background: var(--primary-900);
  border-radius: var(--radius-sm);
}

.data-preview-table-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--primary-950);
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

/* Remove Quasar textarea bottom blue line and animations - ALL STATES */
.q-field__bottom {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  opacity: 0 !important;
  visibility: hidden !important;
}

/* Remove bottom line in all possible states */
.q-field--highlighted .q-field__bottom,
.q-field--focused .q-field__bottom,
.q-field--error .q-field__bottom,
.q-field--standard .q-field__bottom,
.q-field--outlined .q-field__bottom,
.q-field--filled .q-field__bottom,
.q-field--borderless .q-field__bottom,
.q-field .q-field__bottom {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  opacity: 0 !important;
  visibility: hidden !important;
}

/* Remove all animations and transitions from textarea */
textarea,
.q-field textarea,
.q-field__native,
.q-field__control {
  transition: none !important;
  animation: none !important;
}

/* Ensure message input textarea uses full width and proper height */
#message-input {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
  min-width: 0 !important;
  display: block !important;
  white-space: pre-wrap !important;
  word-wrap: break-word !important;
  overflow-wrap: break-word !important;
  word-break: break-word !important;
  position: relative !important;
  height: auto !important;
  min-height: 2.5rem !important;
  max-height: 10rem !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  padding: 0.5rem 0.25rem !important;
}

/* Ensure input card container uses full available width */
.agent-chat-container .chat-messages ~ div {
  width: 100% !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
}

.agent-chat-container .chat-messages ~ div > div:first-child {
  width: 100% !important;
  min-width: 0 !important;
  flex: 1 1 0% !important;
  box-sizing: border-box !important;
  display: block !important;
}

.q-field--focused textarea,
.q-field--focused .q-field__native,
.q-field--highlighted textarea,
.q-field--highlighted .q-field__native {
  transition: none !important;
  animation: none !important;
}

/* Remove ripple effect and other animations */
.q-field__control-container,
.q-field__prepend,
.q-field__append,
.q-field__inner {
  transition: none !important;
  animation: none !important;
}

/* Remove all Quasar field animations and effects */
.q-field,
.q-field__control,
.q-field__native,
.q-field__label {
  transition: none !important;
  animation: none !important;
}

.q-field--focused,
.q-field--highlighted,
.q-field--error {
  transition: none !important;
  animation: none !important;
}

/* Remove underline animation */
.q-field__bottom::before,
.q-field__bottom::after {
  display: none !important;
}

/* Remove any blue line or border animations */
.q-field--focused .q-field__control::after,
.q-field--highlighted .q-field__control::after,
.q-field--focused .q-field__control::before,
.q-field--highlighted .q-field__control::before {
  display: none !important;
  opacity: 0 !important;
  width: 0 !important;
  height: 0 !important;
}

/* Ensure bottom line is hidden in initial state and all variants */
.q-field__bottom *,
.q-field__bottom::before,
.q-field__bottom::after {
  display: none !important;
  height: 0 !important;
  width: 0 !important;
  opacity: 0 !important;
  visibility: hidden !important;
}

/* Force hide bottom line for all textarea fields */
textarea + .q-field__bottom,
.q-field textarea + .q-field__bottom,
.q-field__native + .q-field__bottom {
  display: none !important;
  height: 0 !important;
  opacity: 0 !important;
  visibility: hidden !important;
}

/* Additional rule to ensure no bottom border/line appears */
.q-field:not(.q-field--outlined) .q-field__bottom,
.q-field:not(.q-field--filled) .q-field__bottom,
.q-field:not(.q-field--standard) .q-field__bottom {
  display: none !important;
  height: 0 !important;
  opacity: 0 !important;
  visibility: hidden !important;
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
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Add scrolling class to show scrollbar
        document.body.classList.add('scrolling');
        clearTimeout(scrollTimeout);
        
        // Remove scrolling class after scrolling stops
        scrollTimeout = setTimeout(function() {
            document.body.classList.remove('scrolling');
        }, 500);
        
        if (scrollTop > 50 && !isScrolled) {
            navbar.classList.add('scrolled');
            isScrolled = true;
        } else if (scrollTop <= 50 && isScrolled) {
            navbar.classList.remove('scrolled');
            isScrolled = false;
        }
        
        // Update active nav link based on scroll position
        // If at the top of the page, set Home as active
        if (scrollTop < 100) {
            navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === '#hero-section' || link.getAttribute('href') === '#') {
                    link.classList.add('active');
                }
            });
        }
    });
    
    // Enhanced smooth scrolling for ALL anchor links with precise positioning
    function setupSmoothScrolling(links) {
        links.forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                
                // Handle cross-page hash links (e.g., /dashboard#compare-with-your-model)
                if (href && href.includes('#') && !href.startsWith('#')) {
                    // This is a cross-page link with hash, let it navigate normally
                    // The target page will handle the hash scrolling
                    return; // Don't prevent default, let browser navigate
                }
                
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
                        
                        // Ensure active state is maintained after scroll completes
                        setTimeout(function() {
                            const currentHref = this.getAttribute('href');
                            if (currentHref && currentHref.startsWith('#')) {
                                const targetElement = document.querySelector(currentHref);
                                if (targetElement) {
                                    const rect = targetElement.getBoundingClientRect();
                                    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                                    const elementTop = rect.top + scrollTop;
                                    
                                    // If we're close to the target section, ensure it's active
                                    if (scrollTop >= elementTop - 150 && scrollTop <= elementTop + rect.height + 150) {
                                        navLinks.forEach(l => l.classList.remove('active'));
                                        this.classList.add('active');
                                    }
                                }
                            }
                        }.bind(this), 500);
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
    
    // Initialize active nav link on page load
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    if (scrollTop < 100) {
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#hero-section' || link.getAttribute('href') === '#') {
                link.classList.add('active');
            }
        });
    }
    
    // Intersection Observer for section highlighting with improved precision
    const sections = document.querySelectorAll('section[id], div[id]');
    const observerOptions = {
        threshold: [0.1, 0.3, 0.5],
        rootMargin: '-80px 0px -60% 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        let activeSection = null;
        let maxIntersection = 0;
        
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const intersectionRatio = entry.intersectionRatio;
                if (intersectionRatio > maxIntersection) {
                    maxIntersection = intersectionRatio;
                    activeSection = entry.target;
                }
            }
        });
        
        if (activeSection) {
            const id = activeSection.getAttribute('id');
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            
            // Only update if not at the top (let scroll handler manage Home)
            if (scrollTop >= 100) {
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    const href = link.getAttribute('href');
                    if (href === '#' + id) {
                        link.classList.add('active');
                    }
                });
            }
        }
    }, observerOptions);
    
    sections.forEach(section => {
        const id = section.getAttribute('id');
        // Only observe relevant sections
        if (id && (id === 'mode-selection' || id === 'results' || id === 'documentation' || id === 'about' || id === 'hero-section')) {
            observer.observe(section);
        }
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

    // Function to load example data - unified for both modes
    window.loadExampleData = function(dataset) {
        // Show loading state
        const cards = document.querySelectorAll('.example-data-card');
        cards.forEach(card => {
            card.style.pointerEvents = 'none';
            card.style.opacity = '0.6';
        });

        // Check which mode is currently active
        const agentCardDisplay = document.getElementById('agent-chat-card')?.style.display;
        const manualCardDisplay = document.getElementById('manual-params-card')?.style.display;

        if (agentCardDisplay === 'flex') {
            // Agent mode: use existing agent example data loading
        const buttonId = dataset === 'aou' ? 'example-aou-btn' : 'example-ukbb-btn';
        const button = document.getElementById(buttonId);
        if (button) {
            button.click();
        } else {
            console.error(`Button ${buttonId} not found`);
                // Reset loading state on error
                cards.forEach(card => {
                    card.style.pointerEvents = '';
                    card.style.opacity = '';
                });
            }
        } else if (manualCardDisplay === 'flex') {
            // Manual mode: load example data directly without triggering agent chat
            // Click the corresponding hidden button for manual mode
            const buttonId = dataset === 'aou' ? 'example-manual-aou-btn' : 'example-manual-ukbb-btn';
            const button = document.getElementById(buttonId);
            if (button) {
                button.click();
            } else {
                console.error(`Manual button ${buttonId} not found`);
                // Reset loading state on error
                cards.forEach(card => {
                    card.style.pointerEvents = '';
                    card.style.opacity = '';
                });
            }
        } else {
            console.error('Unable to determine current mode');
            // Reset loading state on error
            cards.forEach(card => {
                card.style.pointerEvents = '';
                card.style.opacity = '';
            });
        }
    };

    // Function to load example data for manual mode
    window.loadManualExampleData = function(dataset) {
        // Click the corresponding hidden button for manual mode
        const buttonId = dataset === 'aou' ? 'example-manual-aou-btn' : 'example-manual-ukbb-btn';
        const button = document.getElementById(buttonId);
        if (button) {
            button.click();
        } else {
            console.error(`Manual button ${buttonId} not found`);
            // Reset loading state on error
            const cards = document.querySelectorAll('.example-data-card');
            cards.forEach(card => {
                card.style.pointerEvents = '';
                card.style.opacity = '';
            });
        }
    };

    window.resetAgentUpload = async function() {
        // First, delete the file from backend if file ID exists
        if (window.currentAgentFileId) {
            try {
                const response = await fetch(`${window.apiBaseUrl}/api/agent/files/${window.currentAgentFileId}`, {
                    method: 'DELETE'
                });
                if (!response.ok) {
                    console.warn('Failed to delete file from backend:', response.statusText);
                }
            } catch (error) {
                console.warn('Error deleting file from backend:', error);
            }
        }

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
        // Clear data preview - restore initial state with example cards
        const previewContainer = document.querySelector('.data-preview-container');
        if (previewContainer) {
            previewContainer.innerHTML = `
                <div style="text-align: center; color: var(--gray-600); padding: 1rem;">
                    <span class="material-symbols-outlined" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block;">description</span>
                    <div style="font-weight: 600; margin-bottom: 0.5rem; font-size: 0.9rem;">No Data Uploaded</div>
                    <div style="font-size: 0.8rem; margin-bottom: 1.5rem;">Click above to upload CSV file</div>

                    <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--gray-200);">
                        <div style="font-size: 0.9rem; font-weight: 600; margin-bottom: 1rem;">Or try with example data:</div>
                        <div class="example-data-cards" style="display: grid; grid-template-columns: 1fr; gap: 1rem; max-width: 400px; margin: 0 auto;">
                            <div class="example-data-card example-data-card-example" onclick="loadExampleData('aou')" style="background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.8) 100%); border: 2px solid rgba(148,163,184,0.3); border-radius: 12px; padding: 1rem; text-align: center; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; display: flex; flex-direction: column; justify-content: center; position: relative; overflow: hidden;">
                                <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(135deg, rgba(59,130,246,0.05) 0%, rgba(147,197,253,0.02) 100%); opacity: 0; transition: opacity 0.3s ease;"></div>

                                <!-- Card Header Structure -->
                                <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem; position: relative; z-index: 1;">
                                    <span class="material-symbols-outlined" style="font-size: 1.5rem; color: #1f2937; margin-right: 0.5rem;">analytics</span>
                                    <div style="font-size: 0.9rem; font-weight: 700; color: #1f2937; margin: 0;">Example Data</div>
                                </div>

                                <!-- Card Description -->
                                <div style="font-size: 0.75rem; line-height: 1.4; color: #6b7280; position: relative; z-index: 1; text-align: left;">
                                    <strong>AUC Performance Dataset:</strong> 164 samples × 6 models with sample identifiers and descriptions
                                    <ul style="margin-top: 0.75rem; padding-left: 0; list-style: none;">
                                        <li style="display: flex; align-items: flex-start; margin-bottom: 0.5rem;">
                                            <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b; margin-right: 0.5rem; flex-shrink: 0; margin-top: 1px;">label</span>
                                            <div><strong>sample_id:</strong> Unique sample identifier (e.g., sample_001, sample_002)</div>
                                        </li>
                                        <li style="display: flex; align-items: flex-start; margin-bottom: 0.5rem;">
                                            <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b; margin-right: 0.5rem; flex-shrink: 0; margin-top: 1px;">label</span>
                                            <div><strong>model_1 to model_6:</strong> AUC performance scores for 6 different models (0.0-1.0 range)</div>
                                        </li>
                                        <li style="display: flex; align-items: flex-start;">
                                            <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b; margin-right: 0.5rem; flex-shrink: 0; margin-top: 1px;">label</span>
                                            <div><strong>description:</strong> Human-readable description for each sample (e.g., "description of sample_001")</div>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        // Clear chat messages - reset to initial welcome message
        const chatMessages = document.querySelector('.chat-messages');
        if (chatMessages) {
            // Clear all messages and restore initial welcome message
            chatMessages.innerHTML = `
                <div class="message assistant" style="display: flex; gap: 0.75rem; margin-bottom: 1rem; align-items: flex-end;">
                    <div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);">
                        <span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">robot_2</span>
                    </div>
                    <div class="message-content" style="flex: 1;">
                        <div class="message-text" style="background: white; padding: 0.75rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200); font-size: 0.8rem; line-height: 1.5; text-align: left; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);">
                            Welcome to SpectralRank! I'm SpectralRank Agent — here to help you navigate and use this platform. I can answer questions, perform ranking analysis, and analyze results. Let me know what you need help with!
                        </div>
                    </div>
                </div>
            `;
        }


        // Clear input field
        const inputField = document.querySelector('.chat-input-area textarea');
        if (inputField) {
            inputField.value = '';
        }
        // Clear global file ID
        window.currentAgentFileId = null;

        // Re-enable attachment button when upload is reset
        const attachmentBtn = document.getElementById('attachment-button');
        if (attachmentBtn) {
            attachmentBtn.classList.remove('disabled');
            attachmentBtn.disabled = false;
        }

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

    // Function to reset shared upload area
    window.resetSharedUpload = async function() {
        // Detect current mode by checking if chat messages container exists (agent mode)
        const chatMessages = document.querySelector('.chat-messages');
        const isAgentMode = chatMessages !== null;
        
        // If agent mode, delete file from backend if file ID exists
        if (isAgentMode && window.currentAgentFileId) {
            try {
                const apiBaseUrl = window.apiBaseUrl || 'http://127.0.0.1:8001';
                const response = await fetch(`${apiBaseUrl}/api/agent/files/${window.currentAgentFileId}`, {
                    method: 'DELETE'
                });
                if (!response.ok) {
                    console.warn('Failed to delete file from backend:', response.statusText);
                }
            } catch (error) {
                console.warn('Error deleting file from backend:', error);
            }
            // Clear the file ID
            window.currentAgentFileId = null;
        }
        
        // Reset upload area UI
        const uploadArea = document.getElementById('shared-upload-area');
        const uploadContent = document.getElementById('shared-upload-content');
        if (uploadArea && uploadContent) {
            uploadArea.classList.remove('uploaded');
            uploadContent.innerHTML = `
                <span class="material-symbols-outlined" style="font-size: 1.2rem; margin-bottom: 0.25rem; display: block; color: #011f5b;">upload_file</span>
                <div style="font-weight: 600; font-size: 0.8rem;">Upload CSV</div>
                <div style="font-size: 0.7rem; color: #666; margin-top: 0.1rem;">Click or drag file</div>
            `;
        }
        
        // Clear the file input
        if (uploadArea) {
            const fileInput = uploadArea.querySelector('input[type="file"]');
            if (fileInput) {
                fileInput.value = '';
            }
        }
        
        // Clear any stored file data
        if (window.manualUploadedFile) {
            window.manualUploadedFile = null;
        }
        
        // Reset data preview
        const previewContainer = document.querySelector('.data-preview-container');
        if (previewContainer) {
            previewContainer.innerHTML = `
                <div style="text-align: center; color: var(--gray-600); padding: 1rem;">
                    <span class="material-symbols-outlined" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block;">description</span>
                    <div style="font-weight: 600; margin-bottom: 0.5rem; font-size: 0.9rem;">No Data Uploaded</div>
                    <div style="font-size: 0.8rem; margin-bottom: 1.5rem;">Click above to upload CSV file</div>

                    <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--gray-200);">
                        <div style="font-size: 0.9rem; font-weight: 600; margin-bottom: 1rem;">Or try with example data:</div>
                        <div class="example-data-cards" style="display: grid; grid-template-columns: 1fr; gap: 1rem; max-width: 400px; margin: 0 auto;">
                            <div class="example-data-card example-data-card-example" onclick="loadExampleData('aou')" style="background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.8) 100%); border: 2px solid rgba(148,163,184,0.3); border-radius: 12px; padding: 1rem; text-align: center; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; display: flex; flex-direction: column; justify-content: center; position: relative; overflow: hidden;">
                                <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(135deg, rgba(59,130,246,0.05) 0%, rgba(147,197,253,0.02) 100%); opacity: 0; transition: opacity 0.3s ease;"></div>

                                <!-- Card Header Structure -->
                                <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem; position: relative; z-index: 1;">
                                    <span class="material-symbols-outlined" style="font-size: 1.5rem; color: #1f2937; margin-right: 0.5rem;">analytics</span>
                                    <div style="font-size: 0.9rem; font-weight: 700; color: #1f2937; margin: 0;">Example Data</div>
                                </div>

                                <!-- Card Description -->
                                <div style="font-size: 0.75rem; line-height: 1.4; color: #6b7280; position: relative; z-index: 1; text-align: left;">
                                    <strong>AUC Performance Dataset:</strong> 164 samples × 6 models with sample identifiers and descriptions
                                    <ul style="margin-top: 0.75rem; padding-left: 0; list-style: none;">
                                        <li style="display: flex; align-items: flex-start; margin-bottom: 0.5rem;">
                                            <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b; margin-right: 0.5rem; flex-shrink: 0; margin-top: 1px;">label</span>
                                            <div><strong>sample_id:</strong> Unique sample identifier (e.g., sample_001, sample_002)</div>
                                        </li>
                                        <li style="display: flex; align-items: flex-start; margin-bottom: 0.5rem;">
                                            <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b; margin-right: 0.5rem; flex-shrink: 0; margin-top: 1px;">label</span>
                                            <div><strong>model_1 to model_6:</strong> AUC performance scores for 6 different models (0.0-1.0 range)</div>
                                        </li>
                                        <li style="display: flex; align-items: flex-start;">
                                            <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b; margin-right: 0.5rem; flex-shrink: 0; margin-top: 1px;">label</span>
                                            <div><strong>description:</strong> Human-readable description for each sample (e.g., "description of sample_001")</div>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // If agent mode, reset chat messages and clear conversation
        if (isAgentMode && chatMessages) {
            chatMessages.innerHTML = `
                <div class="message assistant" style="display: flex; gap: 0.75rem; margin-bottom: 1rem; align-items: flex-end;">
                    <div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);">
                        <span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">robot_2</span>
                    </div>
                    <div class="message-content" style="flex: 1;">
                        <div class="message-text" style="background: white; padding: 0.75rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200); font-size: 0.8rem; line-height: 1.5; text-align: left; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);">
                            Welcome to SpectralRank! I'm SpectralRank Agent — here to help you navigate and use this platform. I can answer questions, perform ranking analysis, and analyze results. Let me know what you need help with!
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Clear input field if exists
        const inputField = document.querySelector('.chat-input-area textarea');
        if (inputField) {
            inputField.value = '';
        }
        
        // Re-enable attachment button when upload is reset
        const attachmentBtn = document.getElementById('attachment-button');
        if (attachmentBtn) {
            attachmentBtn.classList.remove('disabled');
            attachmentBtn.disabled = false;
        }
        
        // Trigger Python-side reset by clicking hidden reset button
        if (isAgentMode) {
            const resetBtn = document.getElementById('reset-agent-upload-btn');
            if (resetBtn) {
                resetBtn.click();
            }
        } else {
            const resetBtn = document.getElementById('reset-manual-upload-btn');
            if (resetBtn) {
                resetBtn.click();
            }
        }
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
def handle_enter_key(e, input_field, messages_container, status_area, send_button, api_key_input):
    """Handle Enter key press to send message"""
    if e.args and e.args.get('key') == 'Enter' and not e.args.get('shiftKey'):
        # Prevent default behavior by triggering the send button click
        # For HTML button, use JavaScript click with the button ID
        ui.run_javascript('document.getElementById("send-button").click()')

def handle_attachment_click():
    """Handle attachment button click - trigger file upload"""
    # Check if data is already uploaded by checking if upload area shows success state
    ui.run_javascript('''
        const uploadArea = document.getElementById('agent-upload-area');
        const attachmentBtn = document.getElementById('attachment-button');

        if (uploadArea && uploadArea.classList.contains('uploaded')) {
            // File already uploaded, disable button and show visual feedback
            if (attachmentBtn) {
                attachmentBtn.classList.add('disabled');
                attachmentBtn.disabled = true;
            }
            console.log('File already uploaded, cannot upload another');
        } else {
            // No file uploaded, enable button and trigger file selection
            if (attachmentBtn) {
                attachmentBtn.classList.remove('disabled');
                attachmentBtn.disabled = false;
            }
            document.getElementById("agent-file-input").click();
        }
    ''')

async def handle_unified_file_upload(e):
    """Unified file upload handler that behaves differently based on current mode"""
    # Validate file type
    if not e.name or not e.name.lower().endswith('.csv'):
        ui.notify('⚠️ Please upload a CSV file only.', type='warning', timeout=3000)
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
        ui.notify('⚠️ File is too large (>50MB). Please use a smaller CSV file.', type='warning', timeout=3000)
        return

    if file_size == 0:
        ui.notify('⚠️ File appears to be empty. Please check your CSV file.', type='warning', timeout=3000)
        return

    # Check which mode is currently active using client state
    state = get_client_state()
    current_mode = state['current_mode']
    is_agent_mode = current_mode == 'agent'
    is_manual_mode = current_mode == 'manual'

    if is_agent_mode:
        # Agent mode: update shared upload area and trigger agent analysis
        await handle_agent_mode_upload(e, content)
    elif is_manual_mode:
        # Manual mode: just update upload status and preview, don't trigger agent chat
        await handle_manual_file_upload(e, content)
    else:
        ui.notify('⚠️ Unable to determine current mode. Please refresh the page.', type='warning', timeout=3000)

async def handle_agent_mode_upload(e, content):
    """Agent mode upload handler - delegates to handle_agent_file_upload for consistency"""

    # Use global references to agent chat components
    global global_messages_container, global_input_field, global_api_key_input

    # Validate file type
    if not e.name or not e.name.lower().endswith('.csv'):
        ui.notify('⚠️ Please upload a CSV file only.', type='warning', timeout=3000)
        return

    # Validate file size (client-side check)
    if hasattr(content, 'seek'):
        content.seek(0, 2)  # Seek to end
        file_size = content.tell()
        content.seek(0)  # Reset to beginning
    else:
        file_size = len(content)

    if file_size > 50 * 1024 * 1024:  # 50MB limit
        ui.notify('⚠️ File is too large (>50MB). Please use a smaller CSV file.', type='warning', timeout=3000)
        return

    if file_size == 0:
        ui.notify('⚠️ File appears to be empty. Please check your CSV file.', type='warning', timeout=3000)
        return

    # Delegate to the same handler used by example data loading
    await handle_agent_file_upload(e, content, global_messages_container, global_input_field, global_api_key_input)

async def handle_manual_file_upload(e, content):
    """Manual mode file upload handler - only updates UI without triggering agent chat"""
    # Update upload area to show uploaded state
    ui.run_javascript(f'''
        const uploadArea = document.getElementById('shared-upload-area');
        const uploadContent = document.getElementById('shared-upload-content');
        if (uploadArea && uploadContent) {{
            uploadArea.classList.add('uploaded');
            uploadContent.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                    <span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">check_circle</span>
                    <div style="text-align: left;">
                        <div style="font-weight: 600; font-size: 0.8rem; color: #1f2937;">File Uploaded</div>
                        <div style="font-size: 0.7rem; color: #4b5563; margin-top: 0.1rem;">{e.name}</div>
                    </div>
                    <button onclick="event.stopPropagation(); resetSharedUpload()" class="upload-delete-btn" style="background: none; border: none; color: #6b7280; cursor: pointer; font-size: 1.2rem; padding: 0.2rem;">×</button>
                </div>
            `;
        }}
    ''')

    # Store file content for manual mode
    state = get_client_state()
    state['manual_uploaded_file'] = {'name': e.name, 'content': content}

    # Update data preview (same as agent mode)
    update_data_preview(content, e.name)

    ui.notify('✅ File uploaded successfully for manual analysis', type='positive', timeout=2000)

# Global variables to store manual mode parameters
manual_params = {
    'b_value': 2000,
    'seed_value': 42,
    'ranking_direction': False  # False = lower is better, True = higher is better
}

async def handle_manual_example_data_load(dataset: str):
    """Manual mode example data loader - loads example data without triggering agent chat"""
    try:
        # Load example data from predefined file paths
        if dataset == 'aou':
            file_path = 'demo_r/example_data.csv'
        elif dataset == 'ukbb':
            file_path = 'demo_r/top2000childrencode_report_ukbb.csv'
        else:
            ui.notify('⚠️ Unknown dataset requested.', type='warning', timeout=3000)
            return

        # Validate file exists
        if not os.path.exists(file_path):
            ui.notify(f'⚠️ Example file not found: {file_path}', type='warning', timeout=3000)
            return

        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()

        # Store in manual mode client state
        state = get_client_state()
        filename = os.path.basename(file_path)
        state['manual_uploaded_file'] = {'name': filename, 'content': content}

        # Update upload area to show uploaded state
        ui.run_javascript(f'''
            const uploadArea = document.getElementById('shared-upload-area');
            const uploadContent = document.getElementById('shared-upload-content');
            if (uploadArea && uploadContent) {{
                uploadArea.classList.add('uploaded');
                uploadContent.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                        <span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">check_circle</span>
                        <div style="text-align: left;">
                            <div style="font-weight: 600; font-size: 0.8rem; color: #1f2937;">File Uploaded</div>
                            <div style="font-size: 0.7rem; color: #4b5563; margin-top: 0.1rem;">{filename}</div>
                        </div>
                        <button onclick="event.stopPropagation(); resetSharedUpload()" class="upload-delete-btn" style="background: none; border: none; color: #6b7280; cursor: pointer; font-size: 1.2rem; padding: 0.2rem;">×</button>
                    </div>
                `;
            }}
        ''')

        # Update data preview
        update_data_preview(content, filename)

        # Reset loading state
        ui.run_javascript('''
            const cards = document.querySelectorAll('.example-data-card');
            cards.forEach(card => {
                card.style.pointerEvents = '';
                card.style.opacity = '';
            });
        ''')

        ui.notify(f'✅ Example {dataset.upper()} data loaded successfully for manual analysis', type='positive', timeout=2000)

    except Exception as e:
        ui.notify(f'⚠️ Failed to load example data: {str(e)}', type='warning', timeout=3000)
        # Reset loading state on error
        ui.run_javascript('''
            const cards = document.querySelectorAll('.example-data-card');
            cards.forEach(card => {
                card.style.pointerEvents = '';
                card.style.opacity = '';
            });
    ''')

async def handle_agent_file_upload(e, content, messages_container, input_field, api_key_input):
    """Enhanced file upload handling with better validation and user feedback"""
    # Validate file type
    if not e.name or not e.name.lower().endswith('.csv'):
        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Please upload a CSV file only.')
        return

    # Validate file size (client-side check)
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
                        ui.run_javascript('resetSharedUpload();')
                        return

                    # Update upload area to show success state and disable attachment button
                    ui.run_javascript(f'''
                        const uploadArea = document.getElementById('shared-upload-area');
                        const uploadContent = document.getElementById('shared-upload-content');
                        const attachmentBtn = document.getElementById('attachment-button');

                        if (uploadArea && uploadContent) {{
                            // Mark upload area as uploaded
                            uploadArea.classList.add('uploaded');
                            uploadContent.innerHTML = `
                                <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                                    <span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">check_circle</span>
                                    <div style="text-align: left;">
                                        <div style="font-weight: 600; font-size: 0.8rem; color: #1f2937;">Ready for Analysis</div>
                                        <div style="font-size: 0.7rem; color: #4b5563; margin-top: 0.1rem;">{e.name}</div>
                                    </div>
                                    <button onclick="event.stopPropagation(); resetSharedUpload()" class="upload-delete-btn"><span class="material-symbols-outlined" style="font-size: 1rem; color: #6b7280;">close</span></button>
                                </div>
                            `;
                        }}

                        // Disable attachment button when file is uploaded
                        if (attachmentBtn) {{
                            attachmentBtn.classList.add('disabled');
                            attachmentBtn.disabled = true;
                        }}
                    ''')

                    # Add user message
                    add_message_to_chat(messages_container, 'user', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">description</span> Uploaded: {e.name}')

                    # Show status panel instead of text message
                    add_status_panel_to_chat(messages_container, api_key_input)

                    # Send initial analysis request to trigger backend workflow
                    ui.timer(2.0, lambda: send_initial_analysis_request(messages_container, file_id, api_key_input), once=True)

                    # Update data preview in left panel (if function exists)
                    try:
                        update_data_preview(content, e.name)
                    except Exception as preview_error:
                        print(f"Preview update error: {preview_error}")

                    # Store file_id in client state and reset conversation history
                    state = get_client_state()
                    state['current_agent_file_id'] = file_id
                    state['agent_conversation_history'] = []  # Reset conversation history for new file

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
                    ui.run_javascript('resetSharedUpload();')

    except asyncio.TimeoutError:
        add_message_to_chat(messages_container, 'assistant', '⏰ Upload timed out. Please try again with a smaller file or check your connection.')
        ui.run_javascript('resetSharedUpload();')

    except Exception as ex:
        error_msg = str(ex)
        if "connection" in error_msg.lower():
            add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">language</span> Upload failed due to connection issues. Please check your internet connection and try again.')
        else:
            add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Upload error: {error_msg}')

        # Reset upload area on error
        ui.run_javascript('resetSharedUpload();')

async def handle_example_data_load(dataset, messages_container, input_field, api_key_input):
    """Load example data - completely mimics handle_agent_file_upload behavior"""
    # Reset card loading state
    ui.run_javascript('''
        const cards = document.querySelectorAll('.example-data-card');
        cards.forEach(card => {
            card.style.pointerEvents = '';
            card.style.opacity = '';
        });
    ''')
    
    try:
        # Determine file path and filename based on dataset
        if dataset == 'aou':
            file_path = 'demo_r/example_data.csv'
            filename = 'example_data.csv'
        elif dataset == 'ukbb':
            file_path = 'demo_r/top2000childrencode_report_ukbb.csv'
            filename = 'top2000childrencode_report_ukbb.csv'
        else:
            file_path = 'demo_r/example_data.csv'
            filename = 'example_data.csv'

        # Show uploading state
        ui.run_javascript(f'''
            const uploadArea = document.getElementById('shared-upload-area');
            const uploadContent = document.getElementById('shared-upload-content');
            if (uploadArea && uploadContent) {{
                uploadArea.classList.add('uploaded');
                uploadContent.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                        <span style="font-size: 1.2rem;">⏳</span>
                        <div style="text-align: left;">
                            <div style="font-weight: 600; font-size: 0.8rem; color: var(--gray-700);">Uploading...</div>
                            <div style="font-size: 0.7rem; color: var(--gray-500); margin-top: 0.1rem;">{filename}</div>
                        </div>
                    </div>
                `;
            }}
        ''')

        # Load example file from backend
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_BASE_URL}/api/agent/load-example',
                json={'file_path': file_path, 'dataset_name': filename},
                timeout=60
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    file_id = result.get('file_id')

                    if not file_id:
                        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Load failed: No file ID returned from server.')
                        ui.run_javascript('resetSharedUpload();')
                        return

                    # Read file content for preview
                    with open(file_path, 'rb') as f:
                        content = f.read()

                    # Update upload area to show success state (exactly like handle_agent_file_upload)
                    ui.run_javascript(f'''
                        const uploadArea = document.getElementById('shared-upload-area');
                        const uploadContent = document.getElementById('shared-upload-content');
                        const attachmentBtn = document.getElementById('attachment-button');
                        if (uploadArea && uploadContent) {{
                            // Mark upload area as uploaded
                            uploadArea.classList.add('uploaded');
                            uploadContent.innerHTML = `
                                <div style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                                    <span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">check_circle</span>
                                    <div style="text-align: left;">
                                        <div style="font-weight: 600; font-size: 0.8rem; color: #1f2937;">Ready for Analysis</div>
                                        <div style="font-size: 0.7rem; color: #4b5563; margin-top: 0.1rem;">{filename}</div>
                                    </div>
                                    <button onclick="event.stopPropagation(); resetSharedUpload()" class="upload-delete-btn"><span class="material-symbols-outlined" style="font-size: 1rem; color: #6b7280;">close</span></button>
                                </div>
                            `;
                        }}

                        // Disable attachment button when file is uploaded
                        if (attachmentBtn) {{
                            attachmentBtn.classList.add('disabled');
                            attachmentBtn.disabled = true;
                        }}
                    ''')

                    # Add user message (exactly like handle_agent_file_upload)
                    add_message_to_chat(messages_container, 'user', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">description</span> Uploaded: {filename}')

                    # Show status panel instead of text message
                    add_status_panel_to_chat(messages_container, api_key_input)

                    # Update data preview (exactly like handle_agent_file_upload)
                    update_data_preview(content, filename)

                    # Store file_id in client state and reset conversation history (exactly like handle_agent_file_upload)
                    state = get_client_state()
                    state['current_agent_file_id'] = file_id
                    state['agent_conversation_history'] = []  # Reset conversation history for new file

                    # Store file_id in JavaScript global for reset function
                    ui.run_javascript(f'window.currentAgentFileId = "{file_id}";')

                    # Send initial analysis request (exactly like handle_agent_file_upload)
                    ui.timer(2.0, lambda: send_initial_analysis_request(messages_container, file_id, api_key_input), once=True)

                    ui.run_javascript('document.querySelector(".chat-messages").scrollTop = document.querySelector(".chat-messages").scrollHeight;')
                else:
                    error_text = await resp.text()
                    add_message_to_chat(messages_container, 'assistant', f'❌ Failed to load example data (HTTP {resp.status}): {error_text}')
                    ui.run_javascript('resetSharedUpload();')

    except asyncio.TimeoutError:
        add_message_to_chat(messages_container, 'assistant', '⏰ Load timed out. Please try again.')
        ui.run_javascript('resetSharedUpload();')
        ui.run_javascript('''
            const cards = document.querySelectorAll('.example-data-card');
            cards.forEach(card => {
                card.style.pointerEvents = '';
                card.style.opacity = '';
            });
        ''')
    except Exception as ex:
        error_msg = str(ex)
        add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">cancel</span> Failed to load example data: {error_msg}')
        ui.run_javascript('resetSharedUpload();')
        ui.run_javascript('''
            const cards = document.querySelectorAll('.example-data-card');
            cards.forEach(card => {
                card.style.pointerEvents = '';
                card.style.opacity = '';
            });
        ''')

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
            table_html += '<div class="data-preview-table-scroll" style="overflow-x: auto; overflow-y: visible; width: 100%; border-radius: 8px; -webkit-overflow-scrolling: touch; position: relative;"><table style="border-collapse: collapse; font-size: 0.75rem; line-height: 1.2; width: max-content; min-width: 100%; table-layout: auto;">'
            # Header row - show all columns with horizontal scrolling
            table_html += '<thead><tr style="background: #011f5b;">'
            for header in headers:  # Show all columns with horizontal scrolling
                table_html += f'<th style="padding: 0.4rem 0.3rem; text-align: left; border: 1px solid var(--gray-200); font-weight: 600; color: white; min-width: 80px;">{header}</th>'
            table_html += '</tr></thead>'

            # Data rows - show all columns with horizontal scrolling
            table_html += '<tbody>'
            for row in data_rows:
                table_html += '<tr style="background: white;">'
                for cell in row:  # Show all columns with horizontal scrolling
                    table_html += f'<td style="padding: 0.4rem 0.3rem; border: 1px solid var(--gray-200); min-width: 80px; text-align: left;">{cell}</td>'
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

def add_status_panel_to_chat(messages_container, api_key_input=None):
    """Add a status panel showing agent workflow progress with sequential loading"""
    global _status_panel_css_added
    state = get_client_state()
    agent_conversation_history = state['agent_conversation_history']
    api_key_confirmed = state['api_key_confirmed']

    # Add CSS animation for spinner (only once)
    if not _status_panel_css_added:
        ui.add_head_html('''
            <style>
                @keyframes status-spin {
                    to { transform: rotate(360deg); }
                }
                @keyframes wave-dots {
                    0%, 60%, 100% { transform: translateY(0); }
                    30% { transform: translateY(-4px); }
                }
                .loading-dots span {
                    display: inline-block;
                    animation: wave-dots 1.2s infinite ease-in-out;
                }
                .loading-dots span:nth-child(1) { animation-delay: 0s; }
                .loading-dots span:nth-child(2) { animation-delay: 0.1s; }
                .loading-dots span:nth-child(3) { animation-delay: 0.2s; }
            </style>
        ''')
        _status_panel_css_added = True

    # Add to conversation history
    agent_conversation_history.append({
        'role': 'assistant',
        'content': 'Status panel: Agent workflow in progress'
    })

    # Keep only last 50 messages to avoid memory issues
    if len(agent_conversation_history) > 50:
        agent_conversation_history = agent_conversation_history[-50:]

    # Check API key status
    api_key_valid = api_key_confirmed
    if api_key_input:
        api_key = api_key_input.value.strip() if hasattr(api_key_input, 'value') else ""
        api_key_valid = api_key_valid and bool(api_key)

    # Status items with sequential loading
    status_items = [
        {'text': 'Verifying OpenAI API key access...', 'status': 'error' if not api_key_valid else 'pending'},
        {'text': 'Analyzing your dataset structure...', 'status': 'pending'},
        {'text': 'Recognizing ranking items...', 'status': 'pending'},
        {'text': 'Determining ranking direction...', 'status': 'pending'},
        {'text': 'Estimating analysis time...', 'status': 'pending'}
    ]

    # If API key is invalid, show error message after the status icon changes
    if not api_key_valid:
        ui.timer(2.0, lambda: add_message_to_chat(messages_container, 'assistant',
            '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">key</span> Please confirm your OpenAI API key first before starting analysis.'), once=True)

    with messages_container:
        with ui.element('div').classes('message assistant').style('''
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1rem;
            align-items: flex-end;
        '''):
            # Assistant avatar
            ui.html('<div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);"><span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">robot_2</span></div>')
            
            # Status panel content
            with ui.element('div').classes('message-content').style('flex: 1;'):
                status_panel = ui.element('div').style('''
                    background: white;
                    padding: 1rem;
                    border-radius: var(--radius-lg);
                    border: 1px solid var(--gray-200);
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
                ''')
                with status_panel:
                    # Header with agent name and icon
                    with ui.element('div').style('display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;'):
                        ui.html('<span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">robot_2</span>')
                        ui.html('<span style="font-weight: 600; font-size: 0.8rem; color: #333;">SpectralRank Agent is working</span>')
                    
                    # Create status item containers that can be updated
                    status_containers = []
                    for i, item in enumerate(status_items):
                        status_row = ui.element('div').style('display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;')
                        with status_row:
                            # Icon container (will be updated) - show initial pending icon
                            icon_container = ui.element('div').style('width: 16px; height: 16px; display: flex; align-items: center; justify-content: center;')
                            with icon_container:
                                if item['status'] == 'pending':
                                    ui.html('<span class="material-symbols-outlined" style="font-size: 0.8rem; color: #fbbf24;">schedule</span>')
                                elif item['status'] == 'error':
                                    ui.html('<span class="material-symbols-outlined" style="font-size: 0.8rem; color: #ef4444;">close</span>')
                                else:
                                    # Empty for other states
                                    pass
                            # Text container
                            ui.html(f'<span style="font-size: 0.8rem; color: #555;">{item["text"]}</span>')
                        status_containers.append({
                            'row': status_row,
                            'icon': icon_container
                        })
                
                # Function to complete "Estimating analysis time..." status
                def complete_recognizing_items_status():
                    """Complete the 'Estimating analysis time...' status item and show Start Ranking button"""
                    global start_ranking_button
                    if len(status_containers) > 4:  # Make sure we have at least 5 items
                        icon_container = status_containers[4]['icon']  # Index 4 is "Estimating analysis time..."
                        icon_container.clear()
                        with icon_container:
                            ui.html('<span class="material-symbols-outlined" style="font-size: 0.8rem; color: #22c55e;">check</span>')

                    # Show the Start Ranking button
                    if start_ranking_button is not None:
                        start_ranking_button.style('display: flex !important;')

                # Sequential loading: update each status item one by one
                def update_status_item(index: int):
                    """Update a status item to loading, then completed"""
                    if index >= len(status_containers):
                        return

                    # Set to loading state
                    icon_container = status_containers[index]['icon']
                    icon_container.clear()
                    with icon_container:
                        ui.html('<div style="width: 13px; height: 13px; border: 2px solid #011f5b; border-top-color: transparent; border-radius: 50%; animation: status-spin 0.8s linear infinite;"></div>')

                    # After delay, set to completed (except for "Estimating analysis time...")
                    def complete_item():
                        icon_container = status_containers[index]['icon']
                        icon_container.clear()
                        with icon_container:
                            # Check the status of this item
                            item_status = status_items[index]['status']
                            if item_status == 'error':
                                ui.html('<span class="material-symbols-outlined" style="font-size: 0.8rem; color: #ef4444;">close</span>')
                                # Don't continue to next item if this one failed
                                return
                            else:
                                ui.html('<span class="material-symbols-outlined" style="font-size: 0.8rem; color: #22c55e;">check</span>')
                        # Move to next item
                        next_index = index + 1
                        if next_index < len(status_containers):
                            def start_next():
                                update_status_item(next_index)
                                # If this is starting "Estimating analysis time..." (index 4), show workflow modal immediately
                                if next_index == 4 and api_key_valid:
                                    def show_workflow():
                                        show_workflow_modal(messages_container, on_complete=complete_recognizing_items_status, api_key_input=api_key_input)
                                    ui.timer(0.1, show_workflow, once=True)  # Show immediately after starting the loading
                            ui.timer(0.8, start_next, once=True)
                        else:
                            # All status items completed - this won't happen since "Estimating analysis time..." waits for workflow modal
                            pass

                    # Special handling for "Estimating analysis time..." (index 4) - don't auto-complete
                    if index == 4:
                        # Don't auto-complete, wait for workflow modal to finish
                        pass
                    else:
                        ui.timer(1.0, complete_item, once=True)  # 1 second delay for all other steps
                
                # Start the sequential loading
                ui.timer(0.5, lambda: update_status_item(0), once=True)
    
    return status_panel

def _format_data_quality_label(code: str) -> str:
    """Map data quality code to display label"""
    if not code:
        return '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'
    normalized = str(code).strip().lower()
    if normalized in ('great', 'good'):
        return 'Great, ready to run perfectly'
    if normalized == 'moderate':
        return 'Moderate, sufficient to run'
    if normalized == 'poor':
        return 'Poor, may fail to run'
    return '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'


def _compute_overall_missing_ratio(missing_ratio_sample: dict) -> str:
    """Compute overall missing ratio percentage string from per-column ratios"""
    try:
        if not missing_ratio_sample:
            return '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'
        values = list(missing_ratio_sample.values())
        if not values:
            return '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'
        avg = sum(float(v) for v in values) / float(len(values))
        pct = round(avg * 100)
        return f'{pct}%'
    except Exception:
        return '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'


def _extract_eta_formatted(data_insights: dict) -> str:
    """Get formatted ETA from insights"""
    try:
        eta = data_insights.get('estimate_runtime', {}) or {}
        eta_str = eta.get('eta_formatted')
        if not eta_str:
            # Some flows may store directly at root
            eta_str = data_insights.get('eta_formatted')
        if not eta_str:
            return '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'
        # Add a leading tilde if not present for approximate
        eta_str = str(eta_str)
        if not eta_str.strip().startswith('~'):
            return f'~{eta_str}'
        return eta_str
    except Exception:
        return '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'


ranking_preview_panel = None
start_ranking_button = None


def show_workflow_modal(messages_container, on_complete=None, api_key_input=None):
    """Display workflow modal panel matching the design from the image exactly"""
    global ranking_preview_panel, start_ranking_button
    state = get_client_state()
    current_agent_file_id = state['current_agent_file_id']
    agent_context = state['agent_context']
    if ranking_preview_panel is None:
        with messages_container:
            with ui.element('div').classes('message assistant').style('''
                display: flex;
                gap: 0.75rem;
                margin-bottom: 1rem;
                align-items: flex-end;
            '''):
                # Assistant avatar
                ui.html('<div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);"><span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">robot_2</span></div>')
                # Workflow panel content
                with ui.element('div').classes('message-content').style('flex: 1;'):
                    ranking_preview_panel = ui.element('div').style('''
                        background: white;
                        padding: 1rem;
                        border-radius: 8px;
                        border: 1px solid #e5e7eb;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
                        text-align: left;
                    ''')
    if ranking_preview_panel is None:
        return ranking_preview_panel
    ranking_preview_panel.clear()
    with ranking_preview_panel:
                    # Header with title and expand icon
                    with ui.element('div').style('''
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        margin-bottom: 0.5rem;
                        text-align: left;
                '''):
                        ui.html('<span style="font-weight: 600; font-size: 0.8rem; color: #333; text-align: left;">Ranking Preview</span>')
                        ui.html('<span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b; cursor: pointer; user-select: none;">open_in_new</span>')
                    
                    # Workflow steps container with connecting line
                    with ui.element('div').style('position: relative;'):
                        # Vertical connecting line between steps
                        ui.html('''
                            <div style="
                                position: absolute;
                                left: 7px;
                                top: 8px;
                                bottom: 8px;
                                width: 2px;
                                background: #e5e7eb;
                                z-index: 0;
                            "></div>
                        ''')
                        
                        # Build Ranking Preview steps from LLM/tool results
                        data_insights = agent_context.get('data_insights', {}) or {}
                        # Step 1: DataQuality
                        missing_ratio_sample = data_insights.get('missing_ratio_sample', {}) or {}
                        analysis_summary = data_insights.get('analysis_summary', {}) or {}
                        data_quality_label = _format_data_quality_label(analysis_summary.get('data_quality'))
                        eta_display = _extract_eta_formatted(data_insights)

                        # Step 2: RankingConfig
                        all_columns = data_insights.get('columns', []) or []
                        items_num = str(len(all_columns)) if all_columns else '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'
                        items_names = ', '.join(all_columns) if all_columns else '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'

                        # Step 3: ParameterSetup - get direction from infer_direction result
                        infer_direction_result = data_insights.get('infer_direction', {}) or {}
                        direction = infer_direction_result.get('direction', 'unsure')
                        direction_error = infer_direction_result.get('error')
                        direction_warning = infer_direction_result.get('data_quality_warning', False)
                        
                        # Format direction display
                        if direction_error or direction_warning:
                            direction_display = f'<span style="color: #f44336;">⚠️ {direction_error or "Mixed directions detected"}</span>'
                        elif direction == 'higher':
                            direction_display = 'higher value is better'
                        elif direction == 'lower':
                            direction_display = 'lower value is better'
                        elif direction == 'mixed':
                            direction_display = '<span style="color: #f44336;">⚠️ Mixed directions - data quality issue</span>'
                        else:
                            direction_display = '<span class="loading-dots"><span>.</span><span>.</span><span>.</span></span>'
                        
                        steps = [
                            {
                                'number': 1,
                                'name': 'DataQuality',
                                'items': [
                                    {'label': 'Missing values', 'value': _compute_overall_missing_ratio(missing_ratio_sample)},
                                    {'label': 'Data quality', 'value': data_quality_label},
                                    {'label': 'Estimated runtime', 'value': eta_display}
                                ]
                            },
                            {
                                'number': 2,
                                'name': 'RankingConfig',
                                'items': [
                                    {'label': 'Ranking items number', 'value': items_num},
                                    {'label': 'Ranking items name', 'value': items_names}
                                ]
                            },
                            {
                                'number': 3,
                                'name': 'ParameterSetup',
                                'items': [
                                    {'label': 'Ranking direction', 'value': direction_display},
                                    {'label': 'Bootstrap iterations', 'value': '2000'},
                                    {'label': 'Random seed', 'value': '42'}
                                ]
                            }
                        ]
                        
                        for idx, step in enumerate(steps):
                            with ui.element('div').style('''
                                display: flex;
                                align-items: flex-start;
                                gap: 0.75rem;
                                margin-bottom: 0.5rem;
                                position: relative;
                                z-index: 1;
                            '''):
                                # Grey circular bullet point (no number)
                                ui.html(f'''
                                    <div style="
                                        width: 16px;
                                        height: 16px;
                                        border-radius: 50%;
                                        background: #e5e7eb;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        flex-shrink: 0;
                                        margin-top: 0.125rem;
                                    "></div>
                                ''')
                            
                                # Step content
                                with ui.element('div').style('flex: 1; text-align: left;'):
                                    # Step name (bold, dark grey/black)
                                    ui.html(f'<div style="font-weight: 600; font-size: 0.8rem; color: #333; margin-bottom: 0.25rem; line-height: 1.2; text-align: left;">{step["name"]}</div>')

                                    # Items info (label: value format with grey tags)
                                    for item in step['items']:
                                        value_tag_html = f'''
                                            <span style="
                                                background: #f3f4f6;
                                                color: #374151;
                                                padding: 0.25rem 0.5rem;
                                                border-radius: 4px;
                                                font-size: 0.8rem;
                                                display: inline-block;
                                                font-family: monospace;
                                            ">{item["value"]}</span>
                                        '''
                                        ui.html(f'<div style="font-size: 0.8rem; color: #6b7280; margin-bottom: 0.25rem; line-height: 1.2; text-align: left;"><span style="font-weight: 400;">{item["label"]}:</span> {value_tag_html}</div>')
                    
                    # Add "Start Ranking" button below the preview steps
                    with ui.element('div').style('margin-top: 1rem; width: 100%;'):
                        async def start_ranking():
                            """Start ranking analysis by calling direct_agent_analysis"""
                            if not current_agent_file_id:
                                add_message_to_chat(messages_container, 'assistant', '❌ No file uploaded. Please upload a file first.')
                                return

                            # Get API key
                            api_key = ""
                            if api_key_input:
                                api_key = api_key_input.value.strip() if hasattr(api_key_input, 'value') else ""

                            if not api_key:
                                add_message_to_chat(messages_container, 'assistant', '❌ Please provide your OpenAI API key first.')
                                return

                            # Call direct_agent_analysis to generate report
                            await direct_agent_analysis(current_agent_file_id, messages_container, api_key)

                        # Create button element with icon and text - initially hidden
                        start_ranking_button = ui.element('button').style('''
                            color: #011f5b !important;
                            background-color: rgba(1, 31, 91, 0.05) !important;
                            border: 1px solid #011f5b !important;
                            border-radius: 6px !important;
                            padding: 6px 16px !important;
                            font-weight: 500 !important;
                            font-size: 0.875rem !important;
                            min-height: 32px !important;
                            transition: all 0.2s ease !important;
                            width: 100%;
                            display: none;  /* Initially hidden */
                            align-items: center;
                            justify-content: center;
                            gap: 0.5rem;
                            cursor: pointer;
                            text-transform: none;
                        ''')
                        start_ranking_button.on('click', start_ranking)
                        # Add icon and text content to button
                        with start_ranking_button:
                            ui.html('<span class="material-symbols-outlined" style="font-size: 1.2rem; vertical-align: middle;">play_arrow</span> Start Ranking')

    # Call completion callback if provided (for timing the status update)
    # Wait a bit to ensure data has been transmitted and processed
    if on_complete:
        def check_data_and_complete():
            # Check if we have the required data insights
            state = get_client_state()
            agent_context = state['agent_context']
            data_insights = agent_context.get('data_insights', {}) or {}
            analysis_summary = data_insights.get('analysis_summary', {}) or {}
            missing_ratio_sample = data_insights.get('missing_ratio_sample', {}) or {}

            # Only complete if we have meaningful data
            if analysis_summary and (missing_ratio_sample or analysis_summary.get('recommended_columns')):
                on_complete()
            else:
                # If data not ready yet, check again after a short delay
                ui.timer(0.5, check_data_and_complete, once=True)

        ui.timer(0.2, check_data_and_complete, once=True)

    return ranking_preview_panel

def add_message_to_chat(messages_container, role, content):
    """Add a message to the chat container and conversation history"""
    state = get_client_state()
    agent_conversation_history = state['agent_conversation_history']

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
            align-items: flex-end;
        '''):
            if role == 'assistant':
                # Assistant: avatar left, content right
                ui.html('<div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);"><span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">robot_2</span></div>')
                with ui.element('div').classes('message-content').style('flex: 1;'):
                    ui.html(f'<div class="message-text" style="background: white; padding: 0.75rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200); font-size: 0.8rem; line-height: 1.5; white-space: pre-wrap; text-align: left; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);">{content}</div>')
            else:
                # User: content left, avatar right
                with ui.element('div').classes('message-content').style('flex: 1;'):
                    ui.html(f'<div class="message-text" style="background: white; padding: 0.75rem; border-radius: 1.25rem; border: 1px solid var(--gray-200); font-size: 0.8rem; line-height: 1.5; white-space: pre-wrap; text-align: left; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);">{content}</div>')
                ui.html('<div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);"><span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">person</span></div>')

async def send_agent_message(hidden_input, messages_container, status_area, api_key_input):
    """Enhanced agent message sending with intelligent context management and user guidance"""
    state = get_client_state()
    api_key_confirmed = state['api_key_confirmed']
    message = hidden_input.value.strip()

    if not message:
        return

    # Clear the hidden input and the visible textarea
    hidden_input.value = ""
    ui.run_javascript('document.getElementById("message-input").value = "";')

    # Check if API key is confirmed
    if not api_key_confirmed:
        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">key</span> Please confirm your OpenAI API key first.')
        return

    api_key = api_key_input.value.strip() if hasattr(api_key_input, 'value') else ""

    # Additional API key validation
    if not api_key:
        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">key</span> Please enter your OpenAI API key first.')
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
    current_agent_file_id = state['current_agent_file_id']
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
            align-items: flex-end;
        ''')
        with typing_indicator:
            ui.html('<div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);"><span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">robot_2</span></div>')
            with ui.element('div').classes('message-content').style('flex: 1;'):
                ui.html('<div class="message-text" style="background: white; padding: 0.75rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200); font-size: 0.8rem; text-align: left; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);"><em>Analyzing your request...</em></div>')

    ui.run_javascript('document.querySelector(".chat-messages").scrollTop = document.querySelector(".chat-messages").scrollHeight;')

    try:
        # Prepare messages for API with enhanced context
        messages = []
        agent_conversation_history = state['agent_conversation_history']
        agent_context = state['agent_context']

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
            payload = {'messages': messages, 'api_key': api_key}
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

                        # Parse tool results from conversation to update data insights
                        try:
                            full_messages = result.get('messages', []) or []
                            insights_update = {}
                            for m in full_messages:
                                if m.get('role') == 'tool':
                                    tool_name = m.get('name')
                                    raw = m.get('content') or '{}'
                                    parsed = {}
                                    try:
                                        import json as _json
                                        # Handle both string and dict content
                                        if isinstance(raw, str):
                                            parsed = _json.loads(raw)
                                        elif isinstance(raw, dict):
                                            parsed = raw
                                        else:
                                            parsed = {}
                                    except Exception:
                                        parsed = {}
                                    if tool_name == 'inspect_dataset' and isinstance(parsed, dict):
                                        # Keep only needed fields
                                        if 'missing_ratio_sample' in parsed:
                                            insights_update['missing_ratio_sample'] = parsed.get('missing_ratio_sample') or {}
                                        if 'analysis_summary' in parsed:
                                            insights_update['analysis_summary'] = parsed.get('analysis_summary') or {}
                                        # Extract ranking columns from LLM analysis
                                        if 'ranking_columns' in parsed:
                                            ranking_cols = parsed.get('ranking_columns', [])
                                            insights_update['columns'] = ranking_cols
                                        # Fallback to old logic if LLM analysis not available
                                        elif 'columns' in parsed:
                                            all_cols = parsed.get('columns', [])
                                            # Filter out common metadata columns
                                            excluded_cols = {'sample_id', 'case_num', 'description', 'case_number', 'id', 'index'}
                                            ranking_cols = [col for col in all_cols if col.lower() not in excluded_cols]
                                            insights_update['columns'] = ranking_cols
                                    elif tool_name == 'infer_direction' and isinstance(parsed, dict):
                                        # Store infer_direction result
                                        insights_update['infer_direction'] = parsed
                                    elif tool_name == 'estimate_runtime' and isinstance(parsed, dict):
                                        # Store under a nested key to avoid collisions
                                        insights_update['estimate_runtime'] = parsed
                            if insights_update:
                                update_agent_context(data=insights_update)
                                try:
                                    # After updating insights, render or refresh the workflow preview with LLM-derived values
                                    show_workflow_modal(messages_container, api_key_input=api_key_input)
                                except Exception:
                                    pass
                        except Exception:
                            # Non-fatal; continue
                            pass

                        if content:
                            # Check if this is a workflow summary message that should show the workflow modal
                            # Skip displaying these messages as they are replaced by the workflow modal
                            if any(phrase in content.lower() for phrase in [
                                'ultra-concise summary',
                                'ultra-concise status',
                                'please choose ranking direction',
                                'please select ranking direction',
                                'please specify ranking direction',
                                'reply: higher',
                                'reply: lower',
                                'higher-is-better',
                                'lower-is-better',
                                'stage 2',
                                'data inspection complete',
                                'next step: please choose',
                                'next step: please specify',
                                'next step',
                                'please specify',
                                'reply with'
                            ]):
                                # Don't display the text message, workflow modal is already shown by status panel completion
                                pass
                            # Check if this is a workflow guidance message
                            elif any(phrase in content.lower() for phrase in ['next step', 'would you like', 'please confirm']):
                                add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">description</span> {content}')
                            else:
                                add_message_to_chat(messages_container, 'assistant', content)

                        # Check for tool calls and display results with enhanced feedback
                        tool_calls = assistant_message.get('tool_calls', [])
                        if tool_calls:
                            for tool_call in tool_calls:
                                func = tool_call.get('function', {})
                                tool_name = func.get('name', 'Unknown Tool')

                                # Skip displaying Phase 1 tool messages (silent execution for initial analysis)
                                # Phase 1 tools: inspect_dataset, infer_direction, estimate_runtime
                                phase1_tools = {'inspect_dataset', 'infer_direction', 'estimate_runtime'}
                                if tool_name not in phase1_tools:
                                    # Provide user-friendly tool descriptions for Phase 2 tools
                                    tool_descriptions = {
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



def get_current_workflow_stage():
    """Determine current workflow stage based on agent state"""
    state = get_client_state()
    current_agent_file_id = state['current_agent_file_id']
    current_agent_job_id = state['current_agent_job_id']
    
    if not current_agent_file_id:
        return "awaiting_upload"
    elif not current_agent_job_id:
        return "data_analysis"
    else:
        return "analysis_running"


# Enhanced context and progress tracking - now client-specific
def update_agent_context(stage=None, data=None, preferences=None):
    """Update agent context and track progress"""
    state = get_client_state()
    agent_context = state['agent_context']

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


# Phase 1 simplified ReAct guidance (for file upload analysis workflow)
PHASE1_SYSTEM_PROMPT_ADDON = """
**CRITICAL: For file upload analysis (Phase 1), you MUST call tools ONE AT A TIME:**

**STEP-BY-STEP WORKFLOW (MANDATORY):**
1. **FIRST**: Call ONLY inspect_dataset(file_id="...") - analyze the data structure
2. **THEN**: Call ONLY infer_direction(columns=[columns from step 1]) - infer ranking direction
3. **FINALLY**: Call ONLY estimate_runtime(n_samples=[rows from step 1], k_methods=[numeric columns from step 1], B=2000)

**ABSOLUTE RULES**:
- NEVER call multiple tools in one response
- NEVER call infer_direction or estimate_runtime before inspect_dataset
- After calling a tool, STOP and wait for the result
- Only call the next tool after receiving the previous tool's result

**COMPLETION RULE**:
- After successfully calling ALL THREE tools in sequence, set 'content' to empty string ("") - NO TEXT RESPONSE
- The UI will handle displaying results to the user

**FORBIDDEN**:
- No text responses during tool calling
- No asking for user input
- No explanations or summaries
- No "please specify" or "next step" phrases
"""


async def send_initial_analysis_request(messages_container, file_id, api_key_input):
    """Send initial analysis request to trigger backend workflow"""
    print(f"DEBUG: Sending analysis request for file_id: {file_id}")
    try:
        state = get_client_state()
        api_key_confirmed = state['api_key_confirmed']

        # Check if API key is confirmed and valid
        api_key = api_key_input.value.strip() if api_key_input else ""
        if not api_key_confirmed or not api_key:
            # API key validation already handled in status panel, just return
            return
        
        # Send a message that will trigger the backend's intelligent analysis workflow
        analysis_message = f"START ANALYSIS - I have uploaded a CSV file with ID: {file_id}. Please immediately use the inspect_dataset tool to analyze the data structure, then infer_direction to determine ranking direction, and estimate_runtime to provide time estimates (use B=2000 for estimation and k_methods equal to length of recommended_columns)."

        # Prepare messages for API with Phase 1 ReAct guidance
        system_content = f'User has uploaded a file with ID: {file_id}. This is a START ANALYSIS request - immediately execute: inspect_dataset → infer_direction → estimate_runtime workflow. When estimating runtime, ALWAYS use B=2000 for preview and set k_methods to the number of recommended_columns (fallback to numeric_candidates length).\n\nCRITICAL: After successfully calling all three tools (inspect_dataset, infer_direction, estimate_runtime), DO NOT generate ANY text response. Set the \'content\' field to an empty string ("") or null - do NOT use the word "EMPTY" as text. The UI will automatically display a Ranking Preview modal where users configure parameters. Do NOT ask users to specify ranking direction or provide any configuration via text.\n\n{PHASE1_SYSTEM_PROMPT_ADDON}'
        
        messages = [
            {'role': 'system', 'content': system_content},
            {'role': 'user', 'content': analysis_message}
        ]

        async with aiohttp.ClientSession() as session:
            payload = {'messages': messages, 'api_key': api_key}
            try:
                async with session.post(f'{API_BASE_URL}/api/agent/chat', json=payload, timeout=60) as resp:
                    if resp.status == 200:
                        result = await resp.json()

                        # Process and display the response (consistent with other flows)
                        if result.get('assistant_message'):
                            assistant_message = result['assistant_message']
                            content = assistant_message.get('content', '')

                            # Parse tool results to update insights
                            phase1_complete = False
                            try:
                                full_messages = result.get('messages', []) or []
                                insights_update = {}
                                phase1_tools_called = set()
                                phase1_tools_attempted = set()  # Track all attempted calls
                                
                                # First pass: collect all tool results
                                for m in full_messages:
                                    if m.get('role') == 'tool':
                                        tool_name = m.get('name')
                                        raw = m.get('content') or '{}'
                                        parsed = {}
                                        try:
                                            import json as _json
                                            # Handle both string and dict content
                                            if isinstance(raw, str):
                                                parsed = _json.loads(raw)
                                            elif isinstance(raw, dict):
                                                parsed = raw
                                            else:
                                                parsed = {}
                                        except Exception:
                                            parsed = {}
                                        
                                        # Track all Phase 1 tool attempts
                                        if tool_name in ['inspect_dataset', 'infer_direction', 'estimate_runtime']:
                                            phase1_tools_attempted.add(tool_name)
                                        
                                        if tool_name == 'inspect_dataset' and isinstance(parsed, dict):
                                            if 'missing_ratio_sample' in parsed:
                                                insights_update['missing_ratio_sample'] = parsed.get('missing_ratio_sample') or {}
                                            if 'analysis_summary' in parsed:
                                                insights_update['analysis_summary'] = parsed.get('analysis_summary') or {}
                                            # Extract ranking columns from LLM analysis
                                            if 'ranking_columns' in parsed:
                                                ranking_cols = parsed.get('ranking_columns', [])
                                                insights_update['columns'] = ranking_cols
                                                print(f"DEBUG FRONTEND: Found ranking_columns: {ranking_cols}")
                                            # Fallback to old logic if LLM analysis not available
                                            elif 'columns' in parsed:
                                                all_cols = parsed.get('columns', [])
                                                # Filter out common metadata columns
                                                excluded_cols = {'sample_id', 'case_num', 'description', 'case_number', 'id', 'index'}
                                                ranking_cols = [col for col in all_cols if col.lower() not in excluded_cols]
                                                insights_update['columns'] = ranking_cols
                                                print(f"DEBUG FRONTEND: Using fallback columns: {ranking_cols}")
                                            else:
                                                print(f"DEBUG FRONTEND: No ranking_columns or columns found in parsed: {list(parsed.keys())}")
                                        elif tool_name == 'infer_direction' and isinstance(parsed, dict):
                                            # Store infer_direction result
                                            insights_update['infer_direction'] = parsed
                                        elif tool_name == 'estimate_runtime' and isinstance(parsed, dict):
                                            insights_update['estimate_runtime'] = parsed
                                
                                # Second pass: determine Phase 1 completion
                                # Check if we have the essential data (ranking columns) and all tools were attempted
                                has_ranking_columns = 'columns' in insights_update and len(insights_update.get('columns', [])) > 0
                                for tool_name in phase1_tools_attempted:
                                    if tool_name == 'inspect_dataset':
                                        # inspect_dataset must succeed (have ranking columns)
                                        if has_ranking_columns:
                                            phase1_tools_called.add(tool_name)
                                    elif tool_name == 'infer_direction':
                                        # infer_direction should succeed, but we can be lenient
                                        phase1_tools_called.add(tool_name)
                                    elif tool_name == 'estimate_runtime':
                                        # estimate_runtime can have errors if we have ranking columns
                                        if has_ranking_columns or 'estimate_runtime' in insights_update:
                                            phase1_tools_called.add(tool_name)
                                
                                # Check if Phase 1 is complete (all three tools called and we have ranking columns)
                                phase1_complete = len(phase1_tools_called) == 3 and has_ranking_columns
                                print(f"DEBUG FRONTEND: Phase 1 status - tools_called: {phase1_tools_called}, has_ranking_columns: {has_ranking_columns}, complete: {phase1_complete}")
                                
                                # Update context with insights (always update to accumulate results)
                                if insights_update:
                                    print(f"DEBUG FRONTEND: Updating insights_update: {insights_update}")
                                    update_agent_context(data=insights_update)
                                    # Verify the update
                                    state = get_client_state()
                                    agent_context = state['agent_context']
                                    data_insights = agent_context.get('data_insights', {})
                                    print(f"DEBUG FRONTEND: After update, data_insights['columns']: {data_insights.get('columns', 'NOT FOUND')}")
                                
                                # Only show workflow modal when Phase 1 is complete (all three tools called)
                                # This ensures estimate_runtime result is available before displaying
                                if phase1_complete:
                                    try:
                                        show_workflow_modal(messages_container, api_key_input=api_key_input)
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                            # Suppress text summaries when Phase 1 is complete (Ranking Preview will be shown)
                            # Completely suppress all text content when Phase 1 is complete, empty, or direction-related
                            
                            # Check if content is empty, whitespace-only, or "EMPTY" string
                            content_str = str(content).strip() if content else ''
                            is_empty_content = (
                                not content_str or 
                                content_str.lower() == 'empty' or
                                len(content_str) == 0
                            )
                            
                            # If Phase 1 is complete or content is empty, completely suppress
                            if phase1_complete or is_empty_content:
                                # Phase 1 complete or empty content - Ranking Preview handles UI, suppress all text
                                pass
                            elif content_str:
                                # Content exists and Phase 1 not complete - check if it should be suppressed
                                lower_c = content_str.lower()
                                
                                # Always suppress direction-related messages
                                direction_keywords = [
                                    'please specify whether higher',
                                    'please specify whether lower',
                                    'specify whether higher values',
                                    'specify whether lower values',
                                    'please choose ranking direction',
                                    'please select ranking direction',
                                    'ranking direction',
                                    'direction for ranking'
                                ]
                                
                                # Check if this is a direction-related message
                                is_direction_message = (
                                    any(keyword in lower_c for keyword in direction_keywords) or
                                    ('specify' in lower_c and 'whether' in lower_c and ('higher' in lower_c or 'lower' in lower_c)) or
                                    ('direction' in lower_c and ('specify' in lower_c or 'choose' in lower_c or 'select' in lower_c))
                                )
                                
                                if is_direction_message:
                                    # Direction message - suppress
                                    pass
                                else:
                                    # Check if content should be suppressed based on other phrases
                                    suppress_phrases = [
                                        'ultra-concise summary',
                                        'reply: higher',
                                        'reply: lower',
                                        'stage 2',
                                        'data inspection complete',
                                        'next step: please choose',
                                        'next step: please specify',
                                        'higher values indicate better',
                                        'higher values indicate worse',
                                        'lower values indicate better',
                                        'lower values indicate worse'
                                    ]
                                    # Check if content contains any suppress phrases
                                    should_suppress = (
                                        any(p in lower_c for p in suppress_phrases) or
                                        any(phrase in lower_c for phrase in ['next step', 'would you like', 'please confirm'])
                                    )
                                    
                                    if not should_suppress:
                                        add_message_to_chat(messages_container, 'assistant', content_str)
                            # If Phase 1 is complete, empty content, or direction-related, completely suppress text content (Ranking Preview handles UI)

                            # Handle tool calls if present
                            tool_calls = assistant_message.get('tool_calls', [])
                            if tool_calls:
                                for tool_call in tool_calls:
                                    func = tool_call.get('function', {})
                                    tool_name = func.get('name', 'Unknown Tool')

                                    # Skip displaying Phase 1 tool messages (silent execution for initial analysis)
                                    # Phase 1 tools: inspect_dataset, infer_direction, estimate_runtime
                                    phase1_tools = {'inspect_dataset', 'infer_direction', 'estimate_runtime'}
                                    if tool_name not in phase1_tools:
                                        # Provide user-friendly tool descriptions for Phase 2 tools
                                        tool_descriptions = {
                                            'create_job': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">rocket_launch</span> Starting analysis job...',
                                            'poll_status': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">analytics</span> Checking progress...',
                                            'get_results': '<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">bar_chart</span> Retrieving results...'
                                        }

                                        friendly_msg = tool_descriptions.get(tool_name, f'<span class="material-symbols-outlined" style="font-size: 0.9rem; vertical-align: middle; margin-right: 0.25rem;">build</span> Executing: {tool_name}...')
                                        add_message_to_chat(messages_container, 'assistant', friendly_msg)

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


async def direct_agent_analysis(file_id: str, messages_container, api_key: str):
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
        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">check_circle</span> <span style="font-weight: 600;">Analysis Complete!</span> Your spectral ranking analysis has finished successfully. Displaying the complete analysis report below.')

        # Add question prompt
        add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">chat</span> You can now ask me questions about your analysis results! Try asking about specific rankings, methods, or interpretations.')

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
    state = get_client_state()
    try:
        # Prepare messages for API with enhanced context
        messages = []
        agent_conversation_history = state['agent_conversation_history']
        current_agent_file_id = state['current_agent_file_id']
        agent_context = state['agent_context']

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
            payload = {'messages': messages, 'api_key': api_key}
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
                            # Check if this is a workflow summary message that should show the workflow modal
                            # Skip displaying these messages as they are replaced by the workflow modal
                            if any(phrase in content.lower() for phrase in [
                                'ultra-concise summary',
                                'ultra-concise status',
                                'please choose ranking direction',
                                'please select ranking direction',
                                'please specify ranking direction',
                                'reply: higher',
                                'reply: lower',
                                'higher-is-better',
                                'lower-is-better',
                                'stage 2',
                                'data inspection complete',
                                'next step: please choose',
                                'next step: please specify',
                                'next step',
                                'please specify',
                                'reply with'
                            ]):
                                # Don't display the text message, workflow modal is already shown by status panel completion
                                pass
                            # Check if this is a workflow guidance message
                            elif any(phrase in content.lower() for phrase in ['next step', 'would you like', 'please confirm']):
                                add_message_to_chat(messages_container, 'assistant', f'<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">description</span> {content}')
                            else:
                                add_message_to_chat(messages_container, 'assistant', content)

                        # Check for tool calls and display results with enhanced feedback
                        tool_calls = assistant_message.get('tool_calls', [])
                        if tool_calls:
                            for tool_call in tool_calls:
                                func = tool_call.get('function', {})
                                tool_name = func.get('name', 'Unknown Tool')

                                # Skip displaying Phase 1 tool messages (silent execution for initial analysis)
                                # Phase 1 tools: inspect_dataset, infer_direction, estimate_runtime
                                phase1_tools = {'inspect_dataset', 'infer_direction', 'estimate_runtime'}
                                if tool_name not in phase1_tools:
                                    # Provide user-friendly tool descriptions for Phase 2 tools
                                    tool_descriptions = {
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
    state = get_client_state()
    state['_analysis_completed'] = True
    return True

def reset_agent_upload_state():
    """Reset the agent upload state"""
    state = get_client_state()
    state['current_agent_file_id'] = None
    state['agent_conversation_history'] = []

def reset_manual_upload_state():
    """Reset the manual upload state"""
    state = get_client_state()
    state['manual_uploaded_file'] = None

def reset_all_page_state():
    """Reset all page state variables on page refresh - client-specific"""
    state = get_client_state()

    # Reset API key confirmation
    state['api_key_confirmed'] = False

    # Reset agent state
    state['current_agent_file_id'] = None
    state['current_agent_job_id'] = None
    state['agent_conversation_history'] = []
    state['_analysis_completed'] = False

    # Reset agent context
    state['agent_context'] = {
        'conversation_history': [],
        'current_stage': 'awaiting_upload',
        'user_preferences': {},
        'data_insights': {},
        'last_activity': None,
    }

    # Reset mode
    state['current_mode'] = 'agent'

    # Reset manual upload state
    state['manual_uploaded_file'] = None

    # Reset chat state
    state['chat_state'] = {
        'messages': [
            {
                'role': 'assistant',
                'content': "Welcome to SpectralRank! I'm SpectralRank Agent — here to help you navigate and use this platform. I can answer questions, perform ranking analysis, and analyze results. Let me know what you need help with!",
            }
        ],
        'uploaded_file_id': None,
        'current_job_id': None,
    }

    # Reset global UI references for workflow modal so that a fresh
    # Ranking Preview panel is created after refresh
    global ranking_preview_panel, start_ranking_button
    ranking_preview_panel = None
    start_ranking_button = None

    # Reset API key input and confirm button UI so that the
    # "Enter OpenAI API Key Here" area always returns to the
    # initial, non-confirmed state after a page refresh.
    global global_api_key_input, global_confirm_button
    try:
        if global_api_key_input is not None:
            global_api_key_input.value = ''
    except Exception:
        # UI might not be fully initialized yet; ignore safely
        pass

    try:
        if global_confirm_button is not None:
            global_confirm_button.text = 'Confirm'
            global_confirm_button.icon = 'check'
            global_confirm_button.style(
                'flex-shrink: 0; '
                'color: #011f5b !important; '
                'background-color: rgba(1, 31, 91, 0.05) !important; '
                'border: 1px solid #011f5b !important; '
                'border-radius: 6px !important; '
                'padding: 8px 16px !important; '
                'font-weight: 500 !important; '
                'font-size: 0.875rem !important; '
                'min-height: 36px !important; '
                'transition: all 0.2s ease !important; '
                'text-transform: none;'
            )
            global_confirm_button.enable()
    except Exception:
        # If button is not ready or already disposed, fail silently
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
                                    summary_msg = '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">check_circle</span> <span style="font-weight: 600;">Analysis Complete!</span> Your spectral ranking analysis has finished successfully. '
                                    if 'methods' in results:
                                        num_rankings = len(results.get('methods', []))
                                        summary_msg += f'Generated {num_rankings} ranking results. '

                                    summary_msg += 'Displaying the complete analysis report now.'
                                    add_message_to_chat(messages_container, 'assistant', summary_msg)

                                    # Add question prompt
                                    ui.timer(0.5, lambda: add_message_to_chat(messages_container, 'assistant', '<span class="material-symbols-outlined" style="font-size: 1rem; vertical-align: middle; margin-right: 0.25rem;">chat</span> You can now ask me questions about your analysis results! Try asking about specific rankings, methods, or interpretations.'), once=True)

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
            ui.html('<a href="#" class="navbar-brand-link">SpectralRank</a>')
        
        # Main navigation menu (hidden on mobile)
        with ui.element('ul').classes('navbar-nav'):
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="#hero-section" class="nav-link active">Home</a>')
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="#mode-selection" class="nav-link">Start Spectral Rank</a>')
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="/dashboard" class="nav-link">LLM Leaderboard</a>')
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="/dashboard#compare-with-your-model" class="nav-link">Rank My LLM</a>')
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="#documentation" class="nav-link">Help</a>')
            with ui.element('li').classes('nav-item'):
                ui.html('<a href="#about" class="nav-link">About</a>')
        
        # Right side actions
        with ui.element('div').classes('navbar-actions'):
            ui.html('<a href="https://github.com/MaxineYu/Spectral_Ranking" class="nav-button primary" target="_blank"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/github/github-original.svg" alt="GitHub" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle;"/>GitHub</a>')
            ui.html('<a href="https://doi.org/10.1287/opre.2023.0439" class="nav-button primary" target="_blank"><img src="https://arxiv.org/static/browse/0.3.4/images/arxiv-logo-one-color-white.svg" alt="arXiv" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle; filter: brightness(0);"/>Read the Paper</a>')
        
        # Mobile menu toggle (visible only on mobile)
        with ui.element('button').classes('mobile-toggle').on('click', toggle_mobile_nav):
            ui.html('☰')
        
        # Mobile navigation menu (hidden by default)
        with ui.element('div').classes('mobile-nav'):
            with ui.element('ul').classes('navbar-nav'):
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#hero-section" class="nav-link active">Home</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#mode-selection" class="nav-link">Start Spectral Rank</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="/dashboard" class="nav-link">LLM Leaderboard</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="/dashboard#compare-with-your-model" class="nav-link">Rank My LLM</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#documentation" class="nav-link">Help</a>')
                with ui.element('li').classes('nav-item'):
                    ui.html('<a href="#about" class="nav-link">About</a>')
            
            with ui.element('div').classes('navbar-actions'):
                ui.html('<a href="https://github.com/MaxineYu/Spectral_Ranking" class="nav-button primary" target="_blank"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/github/github-original.svg" alt="GitHub" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle;"/>GitHub</a>')
                ui.html('<a href="https://doi.org/10.1287/opre.2023.0439" class="nav-button primary" target="_blank"><img src="https://arxiv.org/static/browse/0.3.4/images/arxiv-logo-one-color-white.svg" alt="arXiv" style="height: 1rem; width: auto; display: inline-block; margin-right: 0.5rem; vertical-align: middle; filter: brightness(0);"/>Read the Paper</a>')
    # Enhanced Hero Section with Modern Design - Full screen background
    with ui.element('div').classes('hero-section').style('margin: 0 -1rem; width: calc(100% + 2rem);').props('id="hero-section"'):
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
                    <span style="font-weight: 900; font-size: clamp(2.5rem, 5vw, 4rem); line-height: 1.1; color: #fff; font-family: 'Inter', 'Georgia', serif;">  SpectralRank</span>
                    <img src="https://static.cdnlogo.com/logos/w/18/washington-university-in-st-louis.svg" alt="WUSTL Shield" style="height: 4.8rem; width: auto; display: block; margin: 0; padding: 0;"/>
                </div>
            ''')
            
            # Enhanced Subtitle
            ui.html('''
                <div class="hero-subtitle">
                    Intelligent ranking platform with reliable results and confidence measures.
                </div>
            ''')
            
            # New Feature Highlights
            ui.html('''
                <div class="hero-features">
                    <div class="hero-feature">
                        <span class="material-symbols-outlined hero-feature-icon">warning</span>
                        <div class="hero-feature-title">Traditional Ranking Limited</div>
                        <div class="hero-feature-description">
                            Most ranking methods require homogeneous, complete data and uniform comparison patterns. But real-world data involves heterogeneous comparisons, missing information, and varying scenarios. Traditional approaches fail to handle these practical decision-making challenges effectively.
                        </div>
                    </div>
                    <div class="hero-feature">
                        <span class="material-symbols-outlined hero-feature-icon">trending_up</span>
                        <div class="hero-feature-title">Spectral Ranking Advantage</div>
                        <div class="hero-feature-description">
                            Effectively analyze diverse comparison data—whether complete or partial. Produce reliable rankings that adjust to actual complexities, offering efficient computation and proven reliability for informed decisions free from limiting model assumptions.
                        </div>
                    </div>
                    <div class="hero-feature">
                        <span class="material-symbols-outlined hero-feature-icon">biotech</span>
                        <div class="hero-feature-title">Handles Any Data Type</div>
                        <div class="hero-feature-description">
                            Accommodate various forms of comparison data—from pairwise matchups and multi-item selections to partial datasets with absent entries. Operates smoothly without needing strict model requirements that constrain conventional ranking techniques and their practical use.
                        </div>
                    </div>
                    <div class="hero-feature">
                        <span class="material-symbols-outlined hero-feature-icon">query_stats</span>
                        <div class="hero-feature-title">Trustworthy Ranking Results</div>
                        <div class="hero-feature-description">
                            Obtain rankings accompanied by detailed uncertainty measures and reliability ranges. Identify meaningful ranking distinctions from those that remain uncertain, delivering more dependable understanding compared to basic rankings lacking any uncertainty assessment.
                        </div>
                    </div>
                </div>
            ''')
            
            # Call-to-Action
            ui.html('''
                <div class="hero-cta">
                    <a href="#mode-selection" class="hero-cta-button" style="background: #fff !important; color: #011f5b !important; border: 2.5px solid #011f5b; font-weight: 900; font-size: 1.1rem; transition: background 0.2s, color 0.2s, box-shadow 0.2s; box-shadow: 0 4px 16px rgba(1,31,91,0.10);">
                        Start
                    </a>
                </div>
            ''')

    # Main Container - positioned after full-screen hero
    with ui.element('div').style('width: 100%; max-width: 1400px; margin: 0 auto; padding: 40px 1rem 0 1rem; position: relative; z-index: 2;'):
        
        # Mode Selection Cards (side-by-side) between hero and analysis
        with ui.element('div').style('display: flex; gap: 2rem; width: calc(100% + 2rem); max-width: 1400px; margin: 0rem -1rem; justify-content: center; flex-wrap: wrap; box-sizing: border-box;').props('id="mode-selection"'):
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

        # Unified Analysis Section (shared between agent and manual modes)
        unified_analysis_section = ui.element('section').style('width: calc(100% + 2rem); max-width: 1400px; margin: 1rem -1rem; padding: 0; height: 90vh; display: none; box-sizing: border-box;').props('id="unified-analysis"')

        with unified_analysis_section:
            with ui.element('div').classes('info-card').style('text-align: center; margin: 0; border: 3px solid #011f5b; height: 100%;'):
                # Main layout: Left 2/3 for shared data upload/preview, Right 1/3 for dynamic cards
                with ui.element('div').classes('unified-layout').style('display: flex; height: 100%; gap: 1rem;'):
                    # Left side: Shared data upload and preview area (2/3 width)
                    shared_data_area = ui.element('div').style('''
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

                    # Right side: Dynamic card container (1/3 width) - switches between agent chat and manual parameters
                    dynamic_card_container = ui.element('div').classes('dynamic-card-container').style('''
                        flex: 1;
                        position: relative;
                    ''')

                    # Agent Mode Card (SpectralRank Agent chat interface)
                    with dynamic_card_container:
                        agent_card = ui.element('div').classes('agent-card').style('''
                            position: absolute;
                            top: 0;
                            left: 0;
                            right: 0;
                            bottom: 0;
                        background: rgba(255,255,255,0.95);
                        border-radius: var(--radius-lg);
                        border: 1px solid var(--gray-200);
                        padding: 0;
                            display: none;
                        flex-direction: column;
                        box-shadow: none;
                        backdrop-filter: blur(10px);
                        ''').props('id="agent-chat-card"')

                        # Manual Mode Card (Ranking Configuration)
                        manual_card = ui.element('div').classes('manual-card').style('''
                            position: absolute;
                            top: 0;
                            left: 0;
                            right: 0;
                            bottom: 0;
                            background: rgba(255,255,255,0.95);
                            border-radius: var(--radius-lg);
                            border: 1px solid var(--gray-200);
                            padding: 1.5rem;
                            display: none;
                            flex-direction: column;
                            box-shadow: none;
                            backdrop-filter: blur(10px);
                        ''').props('id="manual-params-card"')

                    # Manual Mode Card Content (Ranking Configuration)
                    with manual_card:
                        with ui.element('div').style('display: flex; align-items: center; justify-content: center; gap: 0.75rem; margin-bottom: 1rem; color: #011f5b;'):
                            ui.html('<span class="material-symbols-outlined" style="font-size: 1.5rem;">settings</span>')
                            ui.html('<h4 style="color: #011f5b; margin: 0; font-weight: 800; font-size: 1.1rem;"><b>Ranking Configuration</b></h4>')
                        ui.html('<p style="color: #6b7280; margin-bottom: 1.5rem;">Configure ranking algorithm settings</p>')
                        with ui.element('div').style('display: flex; flex-direction: column; gap: 1.5rem; text-align: left;'):
                            # Ranking Direction
                            with ui.element('div'):
                                ui.label('Ranking Direction').style('color: #011f5b; font-weight: 600; font-size: 0.95rem; display: block; margin-bottom: 0.5rem; text-align: center;')

                                # State for the custom toggle
                                ranking_direction_state = {'value': 'True'}

                                with ui.row().props('no-wrap').style('width: 100%; display: flex; justify-content: center; flex-direction: column; gap: 0.5rem; align-items: center;'):
                                    # "Higher is Better" button (now on top)
                                    with ui.button('Higher Values are Better').style('width: 100%; max-width: 280px;') as btn_higher:
                                        ui.tooltip('Use for metrics like Accuracy, where a higher number is better.')

                                    # "Lower is Better" button (now on bottom)
                                    with ui.button('Lower Values are Better').style('width: 100%; max-width: 280px;') as btn_lower:
                                        ui.tooltip('Use for metrics like Error Rate, where a lower number is better.')

                                # Apply styles to look like a toggle (vertical layout)
                                btn_higher.props('rounded-t-lg rounded-b-none flat')
                                btn_lower.props('rounded-t-none rounded-b-lg flat')

                                def update_styles(value: str):
                                    global manual_params
                                    ranking_direction_state['value'] = value
                                    manual_params['ranking_direction'] = (value == 'True')
                                    if value == 'True':
                                        # Higher is better selected
                                        btn_higher.props('color=primary')
                                        btn_higher.style('border: 2px solid #011f5b; background: #011f5b !important; color: white !important; opacity: 1.0 !important;')
                                        btn_lower.props('color=grey-4')
                                        btn_lower.style('border: 2px solid #d1d5db; background: #f9fafb !important; color: #9ca3af !important; opacity: 0.6;')
                                    else:
                                        # Lower is better selected
                                        btn_lower.props('color=primary')
                                        btn_lower.style('border: 2px solid #011f5b; background: #011f5b !important; color: white !important; opacity: 1.0 !important;')
                                        btn_higher.props('color=grey-4')
                                        btn_higher.style('border: 2px solid #d1d5db; background: #f9fafb !important; color: #9ca3af !important; opacity: 0.6;')

                                btn_higher.on('click', lambda: update_styles('True'))
                                btn_lower.on('click', lambda: update_styles('False'))

                                update_styles('True') # Apply initial style and sync global params

                            # Advanced Settings Expansion
                            with ui.expansion('Advanced Settings', icon='settings').classes('w-full').style('''
                                background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.9) 100%);
                                border: 1px solid rgba(1,31,91,0.15);
                                border-radius: var(--radius-lg);
                                color: #011f5b;
                                margin-top: 1rem;
                                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
                                transition: all 0.3s ease;
                            '''):
                                with ui.element('div').style('display: flex; flex-direction: column; gap: 1rem; text-align: left; padding: 0.875rem;'):
                                    # Bootstrap Iterations
                                    with ui.element('div'):
                                        with ui.row().style('display: flex; align-items: center; gap: 0.375rem; margin-bottom: 0.375rem;'):
                                            ui.label('Bootstrap Iterations').style('color: #011f5b; font-weight: 600; font-size: 0.8rem;')
                                            with ui.tooltip('Number of bootstrap samples for uncertainty estimation. Higher values increase precision but take longer.').style('background: var(--primary-800); color: white;'):
                                                ui.icon('help_outline', size='xs').style('cursor: help;')
                                        with ui.element('div').style('''
                                            background: white;
                                            border: 1px solid rgba(1,31,91,0.2);
                                            border-radius: var(--radius-md);
                                            padding: 0.375rem 0.5rem;
                                            transition: all 0.2s ease;
                                        '''):
                                            def update_b_value(value):
                                                global manual_params
                                                manual_params['b_value'] = int(value) if value is not None else 2000
                                            B_input = ui.number('', value=2000, min=50, max=5000, step=50, on_change=update_b_value).style('width: 100%; border: none; background: transparent; color: #011f5b; font-weight: 500; font-size: 0.8rem; min-height: 28px; line-height: 1.2; padding: 0;')

                                    # Random Seed
                                    with ui.element('div'):
                                        with ui.row().style('display: flex; align-items: center; gap: 0.375rem; margin-bottom: 0.375rem;'):
                                            ui.label('Random Seed').style('color: #011f5b; font-weight: 600; font-size: 0.8rem;')
                                            with ui.tooltip('Set a fixed number to ensure results are perfectly reproducible. Leave blank for random results.').style('background: var(--primary-800); color: white;'):
                                                ui.icon('help_outline', size='xs').style('cursor: help;')
                                        with ui.element('div').style('''
                                            background: white;
                                            border: 1px solid rgba(1,31,91,0.2);
                                            border-radius: var(--radius-md);
                                            padding: 0.375rem 0.5rem;
                                            transition: all 0.2s ease;
                                        '''):
                                            def update_seed_value(value):
                                                global manual_params
                                                manual_params['seed_value'] = int(value) if value is not None else 42
                                            seed_input = ui.number('', value=42, min=1, max=999999, step=1, on_change=update_seed_value).style('width: 100%; border: none; background: transparent; color: #011f5b; font-weight: 500; font-size: 0.8rem; min-height: 28px; line-height: 1.2; padding: 0;')
                            
                            # Add enhanced CSS for Advanced Settings expansion hover effects
                            ui.add_head_html('''
                                <style>
                                    /* Advanced Settings Expansion Hover Effects */
                                    #manual-params-card .q-expansion-item {
                                        transition: all 0.3s ease !important;
                                    }
                                    #manual-params-card .q-expansion-item:hover {
                                        box-shadow: 0 4px 12px rgba(1, 31, 91, 0.15), 0 2px 6px rgba(0, 0, 0, 0.1) !important;
                                        border-color: rgba(1, 31, 91, 0.25) !important;
                                        transform: translateY(-1px);
                                    }
                                    /* Input field containers hover effect */
                                    #manual-params-card .q-expansion-item__container > div > div > div[style*="background: white"]:hover {
                                        border-color: rgba(1, 31, 91, 0.35) !important;
                                        box-shadow: 0 2px 6px rgba(1, 31, 91, 0.1) !important;
                                    }
                                    /* Input field focus effect */
                                    #manual-params-card .q-expansion-item__container input:focus {
                                        outline: none;
                                    }
                                    #manual-params-card .q-expansion-item__container > div > div > div:has(input:focus) {
                                        border-color: #011f5b !important;
                                        box-shadow: 0 0 0 3px rgba(1, 31, 91, 0.1) !important;
                                    }
                                    /* Make input fields smaller */
                                    #manual-params-card .q-expansion-item__container .q-field {
                                        min-height: auto !important;
                                    }
                                    #manual-params-card .q-expansion-item__container .q-field__control {
                                        min-height: 28px !important;
                                        height: 28px !important;
                                        padding: 0 !important;
                                    }
                                    #manual-params-card .q-expansion-item__container .q-field__control-container {
                                        padding-top: 0 !important;
                                        padding-bottom: 0 !important;
                                    }
                                    #manual-params-card .q-expansion-item__container input {
                                        height: 28px !important;
                                        min-height: 28px !important;
                                        padding: 0 !important;
                                        line-height: 1.2 !important;
                                    }
                                </style>
                            ''')

                        # Generate button
                        with ui.element('div').style('display: flex; justify-content: center; margin-top: 2rem;'):
                            query_button = ui.element('button').style('''
                                color: #011f5b !important;
                                background-color: rgba(1, 31, 91, 0.05) !important;
                                border: 1px solid #011f5b !important;
                                border-radius: 6px !important;
                                padding: 6px 16px !important;
                                font-weight: 500 !important;
                                font-size: 0.875rem !important;
                                min-height: 32px !important;
                                transition: all 0.2s ease !important;
                                width: 100%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                gap: 0.5rem;
                                cursor: pointer;
                                text-transform: none;
                            ''')
                            with query_button:
                                ui.html('<span class="material-symbols-outlined" style="font-size: 1.2rem; vertical-align: middle;">play_arrow</span> Start Ranking')

                    # Data upload and preview area content
                    with shared_data_area:
                        # API Key input section - only shown in agent mode
                        api_key_section = ui.element('div').props('id="api-key-section"').style('margin-bottom: 0.5rem; display: none;')  # Initially hidden
                        with api_key_section:
                            api_key_container = ui.element('div').props('id="api-key-container"').style('margin: 0; max-width: 100%; height: 75px; border: 2px solid #011f5b; border-radius: var(--radius-lg); display: flex; align-items: center; padding: 0 1rem; background: white; transition: all 0.3s ease; gap: 1rem;')
                            with api_key_container:
                                # Left side: Label text with Material Symbols icon
                                ui.html('''
                                    <div style="flex-shrink: 0; color: #011f5b; font-weight: 600; font-size: 0.9rem; white-space: nowrap; display: flex; align-items: center; gap: 0.5rem;">
                                        Enter OpenAI API Key Here <span class="material-symbols-outlined" style="font-size: 1.2rem; vertical-align: middle;">arrow_forward</span>
                                    </div>
                                ''')
                                
                                # Middle: Input field with visibility toggle
                                api_key_input_wrapper = ui.element('div').style('flex: 1; position: relative; display: flex; align-items: center;')
                                with api_key_input_wrapper:
                                    def reset_api_key_confirmation():
                                        state = get_client_state()
                                        api_key_confirmed = state['api_key_confirmed']
                                        if api_key_confirmed:
                                            state['api_key_confirmed'] = False
                                            confirm_button.text = 'Confirm'
                                            confirm_button.icon = 'check'
                                            confirm_button.style('flex-shrink: 0; color: #011f5b !important; background-color: rgba(1, 31, 91, 0.05) !important; border: 1px solid #011f5b !important; border-radius: 6px !important; padding: 8px 16px !important; font-weight: 500 !important; font-size: 0.875rem !important; min-height: 36px !important; transition: all 0.2s ease !important; text-transform: none;')
                                            confirm_button.enable()

                                    api_key_input = ui.input(
                                        placeholder='Enter your OpenAI API key...',
                                        password=True,
                                        on_change=reset_api_key_confirmation,
                                    ).style('flex: 1;').props('id="api-key-input" outlined dense')

                                    # Set global reference
                                    global_api_key_input = api_key_input

                                    # Add custom CSS for input padding and visibility toggle positioning
                                    ui.add_head_html('''
                                        <style>
                                            #api-key-container .q-field__control {
                                                padding-right: 45px !important;
                                            }
                                            #api-key-visibility-toggle {
                                                position: absolute;
                                                right: 8px;
                                                top: 50%;
                                                transform: translateY(-50%);
                                                background: none;
                                                border: none;
                                                cursor: pointer;
                                                padding: 4px;
                                                display: flex;
                                                align-items: center;
                                                color: #666;
                                                z-index: 10;
                                            }
                                            #api-key-visibility-toggle:hover {
                                                color: #011f5b;
                                            }
                                        </style>
                                    ''')
                                    
                                    # Register global function for visibility toggle
                                    ui.add_head_html('''
                                        <script>
                                            if (!window.toggleApiKeyVisibility) {
                                                window.toggleApiKeyVisibility = function() {
                                                    const container = document.getElementById('api-key-container');
                                                    if (!container) return;
                                                    const input = container.querySelector('input[type="password"], input[type="text"]');
                                                    const icon = document.getElementById('api-key-visibility-icon');
                                                    if (input && icon) {
                                                        if (input.type === 'password') {
                                                            input.type = 'text';
                                                            icon.textContent = 'visibility';
                                                        } else {
                                                            input.type = 'password';
                                                            icon.textContent = 'visibility_off';
                                                        }
                                                    }
                                                };
                                            }
                                        </script>
                                    ''')
                                    
                                    # Visibility toggle button using HTML
                                    visibility_toggle_html = ui.html('''
                                        <button id="api-key-visibility-toggle" onclick="window.toggleApiKeyVisibility()">
                                            <span class="material-symbols-outlined" id="api-key-visibility-icon" style="font-size: 1.2rem;">visibility_off</span>
                                        </button>
                                    ''')
                                
                                # Right side: Confirm button - matching dashboard.py Confirm Selection style
                                def confirm_api_key():
                                    state = get_client_state()
                                    api_key_value = api_key_input.value.strip()
                                    if not api_key_value:
                                        ui.notify('⚠️ Please enter your API key', type='warning', timeout=2000)
                                        return

                                    # Basic API key format validation
                                    if len(api_key_value) < 10:
                                        ui.notify('⚠️ API key seems too short. Please check if you entered it correctly.', type='warning', timeout=3000)
                                        return

                                    # Check for obvious invalid input (e.g., pure numbers)
                                    import re
                                    if re.match(r'^\d+$', api_key_value):
                                        ui.notify('⚠️ API key should not be just numbers. Please check your API key format.', type='warning', timeout=3000)
                                        return

                                    # Check if it contains letters (basic validity check)
                                    if not re.search(r'[a-zA-Z]', api_key_value):
                                        ui.notify('⚠️ API key should contain letters. Please check your API key format.', type='warning', timeout=3000)
                                        return

                                    # Set confirmed state and update button
                                    state['api_key_confirmed'] = True
                                    confirm_button.text = 'Confirmed'
                                    confirm_button.icon = 'check_circle'
                                    confirm_button.style('flex-shrink: 0; color: white !important; background-color: #10b981 !important; border: 1px solid #10b981 !important; border-radius: 6px !important; padding: 8px 16px !important; font-weight: 500 !important; font-size: 0.875rem !important; min-height: 36px !important; transition: all 0.2s ease !important; text-transform: none;')
                                    confirm_button.disable()

                                    # Reset chat to initial state after API key confirmation
                                    ui.run_javascript('resetSharedUpload();')

                                    ui.notify('✅ API key confirmed', type='positive', timeout=2000)
                                
                                confirm_button = ui.button('Confirm', icon='check', on_click=confirm_api_key).style('flex-shrink: 0; color: #011f5b !important; background-color: rgba(1, 31, 91, 0.05) !important; border: 1px solid #011f5b !important; border-radius: 6px !important; padding: 8px 16px !important; font-weight: 500 !important; font-size: 0.875rem !important; min-height: 36px !important; transition: all 0.2s ease !important; text-transform: none;').props('id="api-key-confirm-button" outline')

                                # Store global reference to confirm button for later reset
                                set_global_confirm_button(confirm_button)
                        
                        # Unified file upload section (works for both modes)
                        with ui.element('div').style('margin-bottom: 0.5rem;'):
                            # File upload area
                            shared_upload_area = ui.element('div').props('id="shared-upload-area"').style('margin: 0; max-width: 100%; position: relative; height: 75px; cursor: pointer; border: 2px dashed #011f5b; border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; background: rgba(1, 31, 91, 0.1); transition: all 0.3s ease;')
                            with shared_upload_area:
                                ui.html('''
                                    <div id="shared-upload-content" style="text-align: center; color: #011f5b; padding: 0.5rem 0;">
                                        <span class="material-symbols-outlined" style="font-size: 1.2rem; margin-bottom: 0.25rem; display: block; color: #011f5b;">upload_file</span>
                                        <div style="font-weight: 600; font-size: 0.8rem;">Upload CSV</div>
                                        <div style="font-size: 0.7rem; color: #666; margin-top: 0.1rem;">Click or drag file</div>
                                    </div>
                                ''')
                                shared_file_input = ui.upload(on_upload=handle_unified_file_upload, multiple=False, auto_upload=True).props('accept=.csv id="shared-file-input"').style('position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; z-index: 10; cursor: pointer;')
                            shared_upload_area.on('click', lambda: shared_file_input.run_method('pickFiles'))

                        # Data preview section - full space without title
                        with ui.element('div').style('flex: 1; display: flex; flex-direction: column;'):
                            # Data preview container - expanded space
                            data_preview_container = ui.element('div').style('''
                                flex: 1;
                                background: var(--gray-50);
                                border-radius: var(--radius-lg);
                                border: 1px solid var(--gray-200);
                                padding: 1rem;
                                overflow-y: auto;
                                overflow-x: visible;
                                min-height: 400px;
                                max-height: calc(100vh - 300px);
                                overscroll-behavior: contain;
                                -webkit-overflow-scrolling: touch;
                                width: 100%;
                            ''').classes('data-preview-container')

                            # Bind global ref for agent mode report display
                            try:
                                agent_data_preview_ref = data_preview_container
                                print(f"DEBUG: agent_data_preview_ref set to: {agent_data_preview_ref}")
                            except Exception as e:
                                print(f"DEBUG: error setting agent_data_preview_ref: {e}")
                                pass

                            # Hidden buttons to trigger Python functions - placed outside data_preview_container so they won't be deleted on reset
                            # Agent mode example data buttons
                            example_aou_btn = ui.button('Load AOU', on_click=lambda: handle_example_data_load('aou', messages_container, input_field, api_key_input)).props('id="example-aou-btn"').style('display: none;')
                            example_ukbb_btn = ui.button('Load UKBB', on_click=lambda: handle_example_data_load('ukbb', messages_container, input_field, api_key_input)).props('id="example-ukbb-btn"').style('display: none;')

                            # Manual mode example data buttons
                            example_manual_aou_btn = ui.button('Load Manual AOU', on_click=lambda: handle_manual_example_data_load('aou')).props('id="example-manual-aou-btn"').style('display: none;')
                            example_manual_ukbb_btn = ui.button('Load Manual UKBB', on_click=lambda: handle_manual_example_data_load('ukbb')).props('id="example-manual-ukbb-btn"').style('display: none;')
                            
                            # Hidden buttons to trigger Python reset functions
                            reset_agent_upload_btn = ui.button('Reset Agent Upload', on_click=reset_agent_upload_state).props('id="reset-agent-upload-btn"').style('display: none;')
                            reset_manual_upload_btn = ui.button('Reset Manual Upload', on_click=reset_manual_upload_state).props('id="reset-manual-upload-btn"').style('display: none;')
                            reset_all_state_btn = ui.button('Reset All State', on_click=reset_all_page_state).props('id="reset-all-page-state-btn"').style('display: none;')

                            with data_preview_container.classes('data-preview-container'):
                                ui.html('''
                                    <div style="text-align: center; color: var(--gray-600); padding: 1rem;">
                                        <span class="material-symbols-outlined" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block;">description</span>
                                        <div style="font-weight: 600; margin-bottom: 0.5rem; font-size: 0.9rem;">No Data Uploaded</div>
                                        <div style="font-size: 0.8rem; margin-bottom: 1.5rem;">Click above to upload CSV file</div>

                                        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--gray-200);">
                                            <div style="font-size: 0.9rem; font-weight: 600; margin-bottom: 1rem;">Or try with example data:</div>
                                            <div class="example-data-cards" style="display: grid; grid-template-columns: 1fr; gap: 1rem; max-width: 400px; margin: 0 auto;">
                                                <div class="example-data-card example-data-card-example" onclick="loadExampleData('aou')" style="background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.8) 100%); border: 2px solid rgba(148,163,184,0.3); border-radius: 12px; padding: 1rem; text-align: center; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; display: flex; flex-direction: column; justify-content: center; position: relative; overflow: hidden;">
                                                    <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(135deg, rgba(59,130,246,0.05) 0%, rgba(147,197,253,0.02) 100%); opacity: 0; transition: opacity 0.3s ease;"></div>

                                                    <!-- Card Header Structure -->
                                                    <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem; position: relative; z-index: 1;">
                                                        <span class="material-symbols-outlined" style="font-size: 1.5rem; color: #1f2937; margin-right: 0.5rem;">analytics</span>
                                                        <div style="font-size: 0.9rem; font-weight: 700; color: #1f2937; margin: 0;">Example Data</div>
                                                    </div>

                                                    <!-- Card Description -->
                                                    <div style="font-size: 0.75rem; line-height: 1.4; color: #6b7280; position: relative; z-index: 1; text-align: left;">
                                                        <strong>AUC Performance Dataset:</strong> 164 samples × 6 models with sample identifiers and descriptions
                                                        <ul style="margin-top: 0.75rem; padding-left: 0; list-style: none;">
                                                            <li style="display: flex; align-items: flex-start; margin-bottom: 0.5rem;">
                                                                <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b; margin-right: 0.5rem; flex-shrink: 0; margin-top: 1px;">label</span>
                                                                <div><strong>sample_id:</strong> Unique sample identifier (e.g., sample_001, sample_002)</div>
                                                            </li>
                                                            <li style="display: flex; align-items: flex-start; margin-bottom: 0.5rem;">
                                                                <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b; margin-right: 0.5rem; flex-shrink: 0; margin-top: 1px;">label</span>
                                                                <div><strong>model_1 to model_6:</strong> AUC performance scores for 6 different models (0.0-1.0 range)</div>
                                                            </li>
                                                            <li style="display: flex; align-items: flex-start;">
                                                                <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b; margin-right: 0.5rem; flex-shrink: 0; margin-top: 1px;">label</span>
                                                                <div><strong>description:</strong> Human-readable description for each sample (e.g., "description of sample_001")</div>
                                                            </li>
                                                        </ul>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ''')

                    with agent_card:
                        # Add padding wrapper for content - responsive to height changes
                        with ui.element('div').style('padding: 1rem 0.5rem 0 0.5rem; height: 100%; display: flex; flex-direction: column; gap: 0.25rem;'):
                            # Chat header - compact for height responsiveness
                            with ui.element('div').style('display: flex; justify-content: center; margin-bottom: 0; padding: 0.125rem 0 0.75rem 0; border-bottom: 1px solid var(--gray-200); flex-shrink: 0; min-height: 1.5rem;'):
                                ui.html('<h4 style="color: var(--primary-900); margin: 0; padding: 0; font-weight: 800; font-size: 0.875rem; line-height: 1.2;">SpectralRank Agent</h4>')

                            # Messages container - flexible height adaptation
                            messages_container = ui.element('div').classes('chat-messages').style('''
                                flex: 1;
                                overflow-y: auto;
                                padding: 0.25rem;
                                background: var(--gray-50);
                                border-radius: var(--radius-sm);
                                min-height: max(200px, 40vh);
                                max-height: calc(100vh - 200px);
                                overscroll-behavior: contain;
                            ''')

                            # Set global reference
                            global_messages_container = messages_container

                            # Welcome message
                            with messages_container:
                                with ui.element('div').classes('message assistant').style('''
                                    display: flex;
                                    gap: 0.75rem;
                                    margin-bottom: 1rem;
                                    align-items: flex-end;
                                '''):
                                    ui.html('<div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);"><span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">robot_2</span></div>')
                                    with ui.element('div').classes('message-content').style('flex: 1;'):
                                        ui.html('<div class="message-text" style="background: white; padding: 0.75rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200); font-size: 0.8rem; line-height: 1.5; text-align: left; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);">Welcome to SpectralRank! I\'m SpectralRank Agent — here to help you navigate and use this platform. I can answer questions, perform ranking analysis, and analyze results. Let me know what you need help with!</div>')


                            # Input area container (input card + send button)
                            with ui.element('div').style('display: flex; gap: 0.25rem; align-items: stretch; flex-shrink: 0; width: 100%; min-width: 0; box-sizing: border-box;'):
                                # Input card (contains only the text input)
                                with ui.element('div').style('''
                                    background: white;
                                    border: 1px solid var(--gray-200);
                                    border-radius: var(--radius-md);
                                    padding: 0.25rem 0.25rem 0.5rem 0.25rem;
                                    box-shadow: var(--shadow-sm);
                                    flex: 1 1 0%;
                                    display: block;
                                    align-items: flex-start;
                                    min-width: 0;
                                    overflow: visible;
                                    width: 100%;
                                    box-sizing: border-box;
                                    position: relative;
                                '''):
                                    # Create a hidden input field for NiceGUI compatibility
                                    hidden_input = ui.input('').style('display: none;')

                                    input_field = ui.html(f'''
                                        <textarea id="message-input" placeholder="Type your message..."
                                            style="width: 100%; max-width: 100%; box-sizing: border-box; border: none; outline: none; resize: none; font-family: inherit; font-size: 0.8rem; line-height: 1.4; padding: 0.5rem 0.25rem; margin: 0; background: transparent; color: inherit; text-align: left; vertical-align: top; height: auto; min-height: 2.5rem; max-height: 10rem; overflow-y: auto; overflow-x: hidden; overflow-wrap: break-word; word-break: break-word; white-space: pre-wrap; min-width: 0; display: block;"
                                            oninput="document.querySelector('input[type=hidden]').value = this.value; this.style.height = 'auto'; const maxHeightPx = 10 * parseFloat(getComputedStyle(document.documentElement).fontSize); const minHeightPx = 2.5 * parseFloat(getComputedStyle(document.documentElement).fontSize); const newHeight = Math.max(minHeightPx, Math.min(this.scrollHeight, maxHeightPx)); this.style.height = newHeight + 'px';"
                                            onkeydown="if (event.key === 'Enter' && !event.shiftKey) {{
                                                event.preventDefault();
                                                const hiddenInput = document.querySelector('input[type=hidden]');
                                                hiddenInput.value = this.value;
                                                hiddenInput.dispatchEvent(new Event('change'));
                                                this.value = '';
                                                const minHeightPx = 2.5 * parseFloat(getComputedStyle(document.documentElement).fontSize);
                                                this.style.height = minHeightPx + 'px';
                                            }}"></textarea>
                                    ''')

                                    # Set global reference
                                    global_input_field = input_field

                                # Button container (attachment button + send button)
                                with ui.element('div').style('display: flex; flex-direction: column; gap: 0.25rem; align-items: center;'):
                                    # Attachment button
                                    attachment_button = ui.html('''
                                        <button id="attachment-button" class="q-btn q-btn--primary q-btn--actionable q-hoverable q-focusable attachment-btn"
                                                style="height: 32px; width: 32px; flex-shrink: 0; border-radius: var(--radius-md); background: white; border: 2px solid #011f5b; color: #011f5b; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                                            <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b;">attach_file</span>
                                        </button>
                                    ''').on('click', lambda: handle_attachment_click())

                                    # Send button
                                    send_button = ui.html('''
                                        <button id="send-button" class="q-btn q-btn--primary q-btn--actionable q-hoverable q-focusable"
                                                style="height: 32px; width: 32px; flex-shrink: 0; border-radius: var(--radius-md); background: white; border: 2px solid #011f5b; color: #011f5b; display: flex; align-items: center; justify-content: center; cursor: pointer;">
                                            <span class="material-symbols-outlined" style="font-size: 1rem; color: #011f5b;">send</span>
                                        </button>
                                    ''').on('click', lambda: send_agent_message(hidden_input, messages_container, status_area, api_key_input))

                            # Status area - minimal spacing
                            status_area = ui.element('div').style('margin-top: 0; font-size: 0.8rem; color: var(--gray-600); text-align: center;')
                    chat_state = {
                        'messages': [{'role': 'assistant', 'content': 'Welcome to SpectralRank! I\'m SpectralRank Agent — here to help you navigate and use this platform. I can answer questions, perform ranking analysis, and analyze results. Let me know what you need help with!'}],
                        'uploaded_file_id': None,
                        'current_job_id': None
                    }

        def switch_to_agent():
            state = get_client_state()
            state['current_mode'] = 'agent'  # Set client mode state

            # Show unified analysis section
            ui.run_javascript('document.getElementById("unified-analysis").style.display = "block";')

            # Show API key section (agent mode specific)
            ui.run_javascript('document.getElementById("api-key-section").style.display = "block";')

            # Switch to agent mode: show agent chat card, hide manual params card
            ui.run_javascript('''
                const agentChatCard = document.getElementById("agent-chat-card");
                const manualParamsCard = document.getElementById("manual-params-card");
                if (agentChatCard) agentChatCard.style.display = "flex";
                if (manualParamsCard) manualParamsCard.style.display = "none";
            ''')

            # Update mode selection card styles
            ui.run_javascript('''
                const agentCard = document.getElementById("agent-mode-card");
                const manualCard = document.getElementById("manual-mode-card");
                agentCard.classList.add("active");
                agentCard.classList.remove("inactive");
                manualCard.classList.add("inactive");
                manualCard.classList.remove("active");
            ''')

            # Scroll to unified analysis section
            ui.run_javascript('''
                const element = document.getElementById("unified-analysis");
                const elementRect = element.getBoundingClientRect();
                const absoluteElementTop = elementRect.top + window.pageYOffset;
                const middle = absoluteElementTop - (window.innerHeight / 2) + (element.offsetHeight / 2);
                window.scrollTo({top: middle - 20, behavior: "smooth"});
            ''')

        def switch_to_manual():
            state = get_client_state()
            state['current_mode'] = 'manual'  # Set client mode state

            # Show unified analysis section
            ui.run_javascript('document.getElementById("unified-analysis").style.display = "block";')

            # Hide API key section (manual mode doesn't need it)
            ui.run_javascript('document.getElementById("api-key-section").style.display = "none";')

            # Switch to manual mode: show manual params card, hide agent chat card
            ui.run_javascript('''
                const agentChatCard = document.getElementById("agent-chat-card");
                const manualParamsCard = document.getElementById("manual-params-card");
                if (agentChatCard) agentChatCard.style.display = "none";
                if (manualParamsCard) manualParamsCard.style.display = "flex";
            ''')

            # Update mode selection card styles
            ui.run_javascript('''
                const agentCard = document.getElementById("agent-mode-card");
                const manualCard = document.getElementById("manual-mode-card");
                manualCard.classList.add("active");
                manualCard.classList.remove("inactive");
                agentCard.classList.add("inactive");
                agentCard.classList.remove("active");
            ''')

            # Scroll to unified analysis section
            ui.run_javascript('''
                const element = document.getElementById("unified-analysis");
                const elementRect = element.getBoundingClientRect();
                const absoluteElementTop = elementRect.top + window.pageYOffset;
                const middle = absoluteElementTop - (window.innerHeight / 2) + (element.offsetHeight / 2);
                window.scrollTo({top: middle - 30, behavior: "smooth"});
            ''')

        # Set initial state using JavaScript on page load
        # Call Python reset function first
        reset_all_page_state()
        
        ui.add_head_html(f'''
        <script>
        // Initialize API base URL
        window.apiBaseUrl = window.apiBaseUrl || '{API_BASE_URL}';
        
        // Function to reset chat dialog to initial state
        function resetChatDialog() {{
            // Reset chat messages container - clear all messages and restore welcome message
            var messagesContainer = document.querySelector('.chat-messages');
            if (messagesContainer) {{
                messagesContainer.innerHTML = `
                    <div class="message assistant" style="display: flex; gap: 0.75rem; margin-bottom: 1rem; align-items: flex-end;">
                        <div class="message-avatar" style="background: white; color: #011f5b; width: 32px; height: 32px; border-radius: 50%; border: 2px solid #011f5b; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);">
                            <span class="material-symbols-outlined" style="font-size: 1.2rem; color: #011f5b;">robot_2</span>
                        </div>
                        <div class="message-content" style="flex: 1;">
                            <div class="message-text" style="background: white; padding: 0.75rem; border-radius: var(--radius-lg); border: 1px solid var(--gray-200); font-size: 0.8rem; line-height: 1.5; text-align: left; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);">
                                Welcome to SpectralRank! I'm SpectralRank Agent — here to help you navigate and use this platform. I can answer questions, perform ranking analysis, and analyze results. Let me know what you need help with!
                            </div>
                        </div>
                    </div>
                `;
            }}
            
            // Clear input field
            var messageInput = document.getElementById("message-input");
            if (messageInput) {{
                messageInput.value = "";
                const minHeightPx = 2.5 * parseFloat(getComputedStyle(document.documentElement).fontSize);
                messageInput.style.height = minHeightPx + 'px';
            }}
            
            // Reset shared upload area
            if (window.resetSharedUpload) {{
                window.resetSharedUpload();
            }}
            
            // Reset API key confirmation state
            // Find confirm button by its text or icon
            var confirmButtons = document.querySelectorAll('button');
            confirmButtons.forEach(function(btn) {{
                var btnText = btn.textContent || btn.innerText || '';
                var btnIcon = btn.querySelector('.material-symbols-outlined, .q-icon');
                // Check if this is the confirm button (has "Confirm" text or check icon)
                if ((btnText.includes('Confirm') || btnText.includes('Confirmed')) || 
                    (btnIcon && (btnIcon.textContent.includes('check') || btnIcon.textContent.includes('check_circle')))) {{
                    // Reset button to initial state
                    if (btn.disabled) {{
                        btn.disabled = false;
                    }}
                    // Reset button text if it was changed
                    if (btnText.includes('Confirmed')) {{
                        // The button will be recreated by Python, but we can try to reset it
                        var iconSpan = btn.querySelector('.material-symbols-outlined, .q-icon');
                        if (iconSpan && iconSpan.textContent.includes('check_circle')) {{
                            iconSpan.textContent = 'check';
                        }}
                    }}
                }}
            }});
            
            // Clear API key input field
            var apiKeyInput = document.getElementById('api-key-input');
            if (apiKeyInput) {{
                apiKeyInput.value = "";
            }}
            
            // Clear status area
            var statusArea = document.querySelector('.status-area');
            if (statusArea) {{
                statusArea.innerHTML = "";
            }}
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            // Reset chat dialog to initial state on page load
            resetChatDialog();
            
            // Trigger Python-side full state reset so that server state
            // (including API key confirmation and workflow globals) matches
            // the fresh UI after a browser refresh
            var resetStateBtn = document.getElementById('reset-all-page-state-btn');
            if (resetStateBtn) {{
                resetStateBtn.click();
            }}
            
            // Initial state: Unified Analysis section visible, Agent Mode active
            var unifiedAnalysisSection = document.getElementById("unified-analysis");
            var resultsSection = document.getElementById("results");
            if (unifiedAnalysisSection) {{
                unifiedAnalysisSection.style.display = "block";
            }}
            if (resultsSection) resultsSection.style.display = "none";

            // Set initial card visibility: show agent chat card, hide manual params card
            var agentChatCard = document.getElementById("agent-chat-card");
            var manualParamsCard = document.getElementById("manual-params-card");
            if (agentChatCard) agentChatCard.style.display = "flex";
            if (manualParamsCard) manualParamsCard.style.display = "none";

            // Show API key section for agent mode (default mode)
            var apiKeySection = document.getElementById("api-key-section");
            if (apiKeySection) apiKeySection.style.display = "block";

            // Set initial mode selection card styles (Agent Mode active, Manual Mode inactive)
            var agentCard = document.getElementById("agent-mode-card");
            var manualCard = document.getElementById("manual-mode-card");
            if (agentCard) {{
                agentCard.classList.add("active");
                agentCard.classList.remove("inactive");
            }}
            if (manualCard) {{
                manualCard.classList.add("inactive");
                manualCard.classList.remove("active");
            }}
        }});
        
        // Reset on page show (handles browser back/forward navigation)
        window.addEventListener('pageshow', function(event) {{
            // If page was loaded from cache (back/forward navigation), reset the dialog
            if (event.persisted) {{
                resetChatDialog();
                var resetStateBtn = document.getElementById('reset-all-page-state-btn');
                if (resetStateBtn) {{
                    resetStateBtn.click();
                }}
            }}
        }});
        
        // Reset on beforeunload to ensure clean state on refresh
        window.addEventListener('beforeunload', function() {{
            // Clear any stored state that might persist
            if (window.currentAgentFileId) {{
                delete window.currentAgentFileId;
            }}
        }});
        </script>
        ''')

        agent_mode_card.on('click', switch_to_agent)
        manual_mode_card.on('click', switch_to_manual)


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
                
                # Validate input file (check both agent and manual mode files)
                state = get_client_state()
                chat_state = state['chat_state']
                manual_uploaded_file = state['manual_uploaded_file']
                agent_file_available = bool(chat_state.get('uploaded_file_id'))
                manual_file_available = bool(manual_uploaded_file)

                if not agent_file_available and not manual_file_available:
                    ui.notify('🚨 Please upload a CSV file', type='negative')
                    status_container.clear()
                    return

                # Determine which file to use (prefer manual mode if available)
                if manual_file_available:
                    # Use manual mode uploaded file
                    file_bytes = manual_uploaded_file['content']
                    file_name = manual_uploaded_file['name']
                elif agent_file_available:
                    # Get file content from agent uploads
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f'{API_BASE_URL}/api/agent/files/{chat_state["uploaded_file_id"]}', timeout=30) as resp:
                                if resp.status == 200:
                                    file_bytes = await resp.read()
                                    file_name = 'data.csv'  # Default filename
                                else:
                                    raise Exception(f"Server returned status {resp.status}")
                    except Exception as e:
                        ui.notify(f'🚨 Failed to access uploaded file: {str(e)}', type='negative')
                        status_container.clear()
                        return
                else:
                    ui.notify('🚨 No valid file found for analysis', type='negative')
                    status_container.clear()
                    return

                # Use stored parameter values from manual mode, or defaults for agent mode
                global manual_params
                b_value = manual_params['b_value']
                seed_value = manual_params['seed_value']
                ranking_direction = manual_params['ranking_direction']

                # Create job
                job_id, err = await create_job_async(file_name, file_bytes, ranking_direction, b_value, seed_value)
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
                    <span style="font-weight: 900; font-size: 1.5rem;">  SpectralRank</span>
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
                    © 2024 SpectralRank Framework | University of Pennsylvania & Washington University in St. Louis
                </p>
            ''')

# Configure static files
from nicegui import app
app.add_static_files('/static', 'static')


# Enhanced UI configuration with modern theme
ui.run(
    title='SpectralRank',
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
