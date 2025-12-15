"""
Phase 2 Agent Functions for Ranking Results Analysis

This module contains all Phase 2 functionality for handling user questions
about ranking results after analysis is complete.
"""

from typing import Any, Dict, List, Optional
import re
import logging

logger = logging.getLogger(__name__)

# Phase 2 System Prompt Addon
PHASE2_SYSTEM_PROMPT_ADDON = """
**🚨 PHASE 2: RANKING RESULTS ANALYSIS - CRITICAL INSTRUCTIONS 🚨**

**YOUR PRIMARY MISSION: Provide COMPREHENSIVE, DETAILED answers using EXACT data from the ranking results.**

**CRITICAL INSTRUCTIONS - READ CAREFULLY:**

1. **RANKING RESULTS DATA IS PROVIDED IN TWO PLACES:**
   - In the user's message below (appended after their question with clear markers)
   - In the "COMPLETE RANKING RESULTS DATA" section in this system message
   
2. **YOU MUST USE THE ACTUAL DATA PROVIDED - NO EXCEPTIONS:**
   - The user message contains the top 5 methods with exact ranks, names, theta_hat scores, and confidence intervals
   - The system context contains ALL methods with complete statistics
   - USE THESE EXACT NUMBERS - do NOT give generic answers like "various models" or "higher-ranked models"
   - If you don't see the data, LOOK AGAIN - it's definitely there
   
3. **REQUIRED ANSWER FORMAT (MANDATORY):**
   When answering "Explain what these ranking results mean" or similar questions, you MUST:
   - Start with: "Based on your ranking analysis results:" or similar
   - List the top 3-5 methods BY THEIR EXACT NAMES (not "top performers" or "better models")
   - Include EXACT ranks (1, 2, 3, etc.) and EXACT theta_hat scores (e.g., 0.8523, not "high scores")
   - Include EXACT confidence intervals as integers (e.g., [1, 2] NOT [0.84, 0.87] or [1.0000, 2.0000])
   - Calculate and mention the performance gap between #1 and #2 using the actual numbers
   - Explain what the ranking direction means (higher/lower-is-better) for THIS specific dataset
   - Reference the analysis parameters (B, seed, direction) from the data
   - Be COMPLETE - don't ask if they want more details, just provide them
   
4. **FORBIDDEN RESPONSES (YOUR ANSWER WILL BE REJECTED):**
   - ❌ "The ranking results show the relative performance of various models" (TOO GENERIC - USE METHOD NAMES)
   - ❌ "Higher-ranked models perform better" (SAY WHICH ONES SPECIFICALLY)
   - ❌ "Please specify your ranking results" (THE DATA IS PROVIDED BELOW)
   - ❌ "I don't have access to the results" (YOU DO - IT'S IN THE USER MESSAGE AND SYSTEM CONTEXT)
   - ❌ "If you'd like, I can provide a detailed interpretation" (JUST PROVIDE IT NOW)
   - ❌ Any answer that doesn't include at least 3 specific method names with exact ranks and scores

1. **Comprehensive Answer Strategy**:
   - **ALWAYS include specific data**: Use exact values from the ranking results (ranks, theta_hat scores, confidence intervals)
   - **Provide complete context**: Explain what the ranking means, how it was calculated, and what the numbers represent
   - **Include actionable insights**: Not just what the results show, but what they mean for decision-making
   - **Reference multiple methods**: When discussing top methods, mention top 3-5 with their specific rankings and scores
   - **Explain statistical significance**: Discuss confidence intervals and what they mean for reliability

2. **Answer Structure for Interpretation Questions**:
   When users ask "What do these results mean?" or "Explain the ranking results", provide:
   
   a) **Executive Summary** (2-3 sentences):
      - What the ranking shows overall
      - Which methods performed best/worst
      - Key takeaway
   
   b) **Detailed Breakdown**:
      - Top 3-5 methods with exact ranks, theta_hat scores, and confidence intervals
      - Ranking direction explanation (higher/lower is better and why)
      - Statistical confidence and reliability assessment
      - Notable patterns or gaps between methods
   
   c) **Practical Implications**:
      - What these results suggest for method selection
      - Confidence level in the rankings
      - Any caveats or limitations
   
   d) **Technical Context** (brief):
      - Analysis parameters used (B bootstrap iterations, seed, direction)
      - Methodology (spectral ranking)
      - Dataset characteristics if available

3. **Data Usage Requirements**:
   - **ALWAYS cite specific numbers** from the ranking results provided in context
   - Use method names exactly as they appear in the results
   - Include confidence intervals when available
   - Compare methods quantitatively (e.g., "Method A ranks #1 with θ=0.85, while Method B ranks #2 with θ=0.72")
   - Calculate and mention gaps between methods when relevant

4. **Answer Completeness Checklist**:
   ✓ Did I include specific ranking numbers?
   ✓ Did I explain what the ranking direction means?
   ✓ Did I mention top 3-5 methods with their scores?
   ✓ Did I discuss statistical confidence?
   ✓ Did I provide actionable insights?
   ✓ Did I avoid asking follow-up questions?

**EXAMPLE ANSWER FOR "Explain what these ranking results mean" (YOU MUST FOLLOW THIS FORMAT):**

"Based on your ranking analysis results:

**Top Ranked Methods:**

1. **[EXACT METHOD NAME FROM DATA]** ranks #1 with θ=0.8523 (95% CI: [1, 2])
   - This method significantly outperforms all others with the highest theta_hat score
   - The confidence interval shows the rank is stable between rank 1 and 2
   - This is the clear top performer

2. **[EXACT METHOD NAME FROM DATA]** ranks #2 with θ=0.7234 (95% CI: [2, 3])
   - Strong performance but notably lower than #1
   - Performance gap: 0.1289 (17.8% relative difference) - this is a significant gap
   - The confidence intervals do not overlap with #1, confirming statistical significance

3. **[EXACT METHOD NAME FROM DATA]** ranks #3 with θ=0.6891 (95% CI: [3, 3])
   - Competitive performance but with some uncertainty
   - Gap from #2: 0.0343 (4.7% relative difference)

**Interpretation:**

Since your analysis used **higher-is-better** direction (based on the parameters: B=2000, seed=42), higher theta_hat values indicate better performance. The ranking shows that [Method Name #1] is the clear top choice with a substantial advantage over other methods.

**Statistical Confidence:**

The confidence intervals show that the top method is statistically distinct from others (non-overlapping CIs between #1 and #2), suggesting reliable ranking. The analysis used B=2000 bootstrap iterations, ensuring robust statistical confidence.

**Practical Implications:**

Based on these results, **[EXACT METHOD NAME FROM DATA]** is the recommended choice for your dataset, with a significant performance advantage of 0.1289 (17.8% relative improvement) over the second-ranked method."

**CRITICAL: Replace [EXACT METHOD NAME FROM DATA] with the actual method names from the ranking results provided below. Use the exact numbers, not approximations.**
"""

# Phase 2 Question Types and Answer Strategies
PHASE2_QUESTION_TYPES = """
**Question Types and Answer Strategies:**

1. **Ranking Questions** (e.g., "Which method is ranked highest?", "What's the top method?")
   - Provide direct answer with method name
   - Include ranking position and theta_hat score
   - Reference confidence intervals if available

2. **Comparison Questions** (e.g., "How does method A compare to method B?", "Compare X and Y")
   - Provide quantitative comparison (ranks, scores, confidence intervals)
   - Mention statistical significance if confidence intervals overlap
   - Explain practical implications

3. **Interpretation Questions** (e.g., "What does this ranking mean?", "Explain the results")
   - **Provide COMPLETE, DETAILED explanation** - don't just summarize, give full context
   - List top 3-5 methods with exact ranks, theta_hat scores, and confidence intervals
   - Explain ranking direction (higher/lower is better) and what it means for this dataset
   - Discuss statistical significance: mention confidence intervals and what overlapping/non-overlapping CIs mean
   - Identify performance gaps: calculate and mention differences between methods
   - Provide actionable insights: what should users do based on these results?
   - Reference analysis parameters (B, seed, direction) and methodology
   - **DO NOT ask "Would you like more details?" - just provide all details upfront**

4. **Technical Questions** (e.g., "How was the ranking calculated?", "What is theta_hat?")
   - Explain the spectral ranking methodology
   - Reference parameters used (B, seed)
   - Keep explanation accessible but accurate

5. **Specific Method Questions** (e.g., "Tell me about method X", "What's the rank of Y?")
   - Provide exact rank, theta_hat, and confidence interval
   - Compare with other methods if relevant
   - Explain what the values mean
"""


def prepare_phase2_messages(
    user_message: str,
    ranking_results: Dict[str, Any],
    conversation_history: List[Dict],
    base_system_prompt: str = ""
) -> List[Dict]:
    """
    Prepare Phase 2 messages with ranking results context.
    
    Args:
        user_message: The user's current message
        ranking_results: Complete ranking results dictionary
        conversation_history: Previous conversation messages
        base_system_prompt: Base system prompt to prepend (optional)
    
    Returns:
        List of message dictionaries ready for OpenAI API
    """
    messages = []
    
    # Debug: Check ranking_results
    print(f"DEBUG prepare_phase2_messages: ranking_results is None: {ranking_results is None}")
    if ranking_results:
        print(f"DEBUG prepare_phase2_messages: ranking_results type: {type(ranking_results)}, keys: {list(ranking_results.keys()) if isinstance(ranking_results, dict) else 'NOT DICT'}")
        methods = ranking_results.get('methods', [])
        print(f"DEBUG prepare_phase2_messages: methods count: {len(methods)}")
        if methods:
            print(f"DEBUG prepare_phase2_messages: First method: {methods[0]}")
            print(f"DEBUG prepare_phase2_messages: Method names: {[m.get('name') for m in methods[:3]]}")
        else:
            print(f"DEBUG prepare_phase2_messages: WARNING - ranking_results exists but methods list is empty!")
            print(f"DEBUG prepare_phase2_messages: ranking_results content: {str(ranking_results)[:500]}")
    
    if ranking_results and ranking_results.get('methods'):
        methods = ranking_results.get('methods', [])
        sorted_methods = sorted(methods, key=lambda x: x.get('rank', 999))
        top_5 = sorted_methods[:5]
        
        # Build results summary for context
        results_summary = {
            'total_methods': len(methods),
            'top_5': [
                {
                    'name': m.get('name'),
                    'rank': m.get('rank'),
                    'theta_hat': m.get('theta_hat'),
                    'ci': m.get('ci_two_sided', [None, None])
                }
                for m in top_5
            ],
            'params': ranking_results.get('params', {}),
            'metadata': ranking_results.get('metadata', {})
        }
        
        # Format context message with comprehensive details
        context_lines = [
            f"**COMPLETE RANKING RESULTS DATA:**",
            f"",
            f"**Overview:**",
            f"- Total methods ranked: {results_summary['total_methods']}",
        ]
        
        # Add analysis parameters first for context
        params = results_summary['params']
        direction = 'higher' if params.get('bigbetter') else 'lower'
        direction_desc = 'higher values are better' if params.get('bigbetter') else 'lower values are better'
        context_lines.extend([
            f"- Ranking direction: {direction} ({direction_desc})",
            f"- Bootstrap iterations (B): {params.get('B', 'N/A')}",
            f"- Random seed: {params.get('seed', 'N/A')}",
            f"",
        ])
        
        # Add metadata if available
        metadata = results_summary['metadata']
        if metadata:
            if metadata.get('n_samples'):
                context_lines.append(f"- Dataset size: {metadata.get('n_samples')} samples")
            if metadata.get('runtime_sec'):
                context_lines.append(f"- Analysis runtime: {metadata.get('runtime_sec'):.2f} seconds")
            context_lines.append("")
        
        # Detailed top methods with full statistics
        context_lines.append(f"**TOP {len(results_summary['top_5'])} RANKED METHODS (with complete statistics):**")
        for method in results_summary['top_5']:
            # Handle CI values - always format as integers (no decimals)
            ci = method['ci']
            if ci and ci[0] is not None and ci[1] is not None:
                if isinstance(ci[0], (int, float)) and isinstance(ci[1], (int, float)):
                    # Always format as integers (round to nearest integer)
                    ci_str = f"[{int(round(ci[0]))}, {int(round(ci[1]))}]"
                    ci_width = None
                else:
                    ci_str = "N/A"
                    ci_width = None
            else:
                ci_str = "N/A"
                ci_width = None
            
            context_lines.append(
                f"  Rank {method['rank']}: {method['name']}"
            )
            context_lines.append(
                f"    - Theta_hat (ranking score): {method['theta_hat']:.4f}"
            )
            if ci_str != "N/A":
                context_lines.append(
                    f"    - 95% Confidence Interval: {ci_str}"
                )
            context_lines.append("")
        
        # Add performance gap analysis
        if len(results_summary['top_5']) >= 2:
            top_theta = results_summary['top_5'][0]['theta_hat']
            second_theta = results_summary['top_5'][1]['theta_hat']
            gap = abs(top_theta - second_theta)
            gap_percent = (gap / max(abs(top_theta), abs(second_theta))) * 100 if max(abs(top_theta), abs(second_theta)) > 0 else 0
            context_lines.extend([
                f"**Performance Gap Analysis:**",
                f"- Gap between #1 and #2: {gap:.4f} ({gap_percent:.1f}% relative difference)",
                f"- This indicates {'significant' if gap > 0.05 else 'moderate' if gap > 0.02 else 'small'} performance difference",
                f"",
            ])
        
        # Add all methods for comprehensive reference
        context_lines.append(f"**ALL RANKED METHODS (for reference):**")
        for method in sorted_methods:
            ci = method.get('ci_two_sided', [None, None])
            if ci and ci[0] is not None and ci[1] is not None:
                # Always format CI as integers (no decimals)
                if isinstance(ci[0], (int, float)) and isinstance(ci[1], (int, float)):
                    ci_str = f"[{int(round(ci[0]))}, {int(round(ci[1]))}]"
                else:
                    ci_str = "N/A"
            else:
                ci_str = "N/A"
            context_lines.append(
                f"  {method.get('rank')}. {method.get('name')}: θ={method.get('theta_hat', 0):.4f}, CI: {ci_str}"
            )
        
        system_context = "\n".join(context_lines)
        
        # Build a SIMPLIFIED, DATA-FIRST system message
        # Strategy: Put data FIRST, then MINIMAL but STRONG instructions
        full_system_content = ""
        
        # STEP 1: DATA FIRST - Most prominent position
        full_system_content += "="*100 + "\n"
        full_system_content += "🚨🚨🚨 RANKING RESULTS DATA - YOU MUST USE THESE EXACT NUMBERS 🚨🚨🚨\n"
        full_system_content += "="*100 + "\n\n"
        full_system_content += system_context + "\n\n"
        full_system_content += "="*100 + "\n\n"
        
        # STEP 2: MINIMAL BUT STRONG INSTRUCTIONS
        full_system_content += """**CRITICAL INSTRUCTIONS - READ CAREFULLY:**

The user is asking about THEIR SPECIFIC ranking results. The complete data is PROVIDED ABOVE in the "COMPLETE RANKING RESULTS DATA" section.

**YOU MUST ANSWER THIS QUESTION. DO NOT REFUSE OR REDIRECT.**

**YOU MUST:**
1. Start your answer with: "Based on your ranking analysis results:"
2. List the top 3-5 methods BY THEIR EXACT NAMES (from the data above) with exact ranks and theta_hat scores
3. Use the EXACT numbers from the data above - do NOT use generic phrases
4. **CRITICAL: When displaying confidence intervals, ALWAYS format them as integers (e.g., [1, 2] NOT [1.0000, 2.0000])**
5. Explain what the ranking direction means for this specific dataset
5. Provide a COMPLETE, DETAILED explanation - do not ask if they want more details

**FORBIDDEN - DO NOT SAY:**
- "Please specify the ranking method" (THE DATA IS ABOVE)
- "Please note that I can only assist" (YOU MUST ANSWER - THE DATA IS PROVIDED)
- "kindly refer to the results presentation" (YOU ARE THE RESULTS PRESENTATION - ANSWER NOW)
- "If you want, I can help" (JUST HELP NOW - PROVIDE THE ANSWER)
- "various models" or "higher-ranked models" (USE ACTUAL METHOD NAMES FROM DATA ABOVE)
- "If you'd like, I can provide" (JUST PROVIDE IT NOW)

**EXAMPLE FORMAT:**
"Based on your ranking analysis results:

**Top Ranked Methods:**
1. [EXACT METHOD NAME FROM DATA ABOVE] ranks #1 with θ=[EXACT NUMBER FROM DATA] (95% CI: [1, 2])
2. [EXACT METHOD NAME FROM DATA ABOVE] ranks #2 with θ=[EXACT NUMBER FROM DATA] (95% CI: [2, 3])
3. [EXACT METHOD NAME FROM DATA ABOVE] ranks #3 with θ=[EXACT NUMBER FROM DATA] (95% CI: [3, 3])

**IMPORTANT: Confidence intervals must be displayed as integers (e.g., [1, 2] NOT [1.0000, 2.0000])**

[Then explain what these numbers mean, the ranking direction, performance gaps, etc.]"

**THE DATA IS ABOVE. USE IT NOW. DO NOT ASK FOR DATA. DO NOT REFUSE TO ANSWER.**
"""
        
        # Add system message with Phase 2 guidance
        messages.append({
            'role': 'system',
            'content': full_system_content
        })
    else:
        # If ranking_results is missing or empty, provide clear error message
        error_message = """
**ERROR: Ranking results data is not available.**

The ranking results should have been provided in the context, but they are missing or empty.
Please check that:
1. The ranking analysis has completed successfully
2. The results contain a 'methods' field with ranking data
3. The results are being passed correctly to this function

**DO NOT ask the user to upload data or specify results. Instead, inform them that there is a technical issue and the results need to be regenerated.**
"""
        messages.append({
            'role': 'system',
            'content': error_message
        })
        print(f"DEBUG prepare_phase2_messages: ERROR - ranking_results missing or empty!")
    
    # Add recent conversation history (last 10 messages, excluding system messages)
    recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
    for msg in recent_history:
        if msg.get('role') != 'system':  # Skip system messages in history
            messages.append({
                'role': msg.get('role'),
                'content': msg.get('content')
            })
    
    # Add current user message WITH ranking data embedded directly
    # This ensures Agent sees the data even if it doesn't read system message carefully
    if ranking_results and ranking_results.get('methods'):
        # Create a comprehensive data summary to append to user message
        methods = ranking_results.get('methods', [])
        sorted_methods = sorted(methods, key=lambda x: x.get('rank', 999))
        top_5 = sorted_methods[:5]  # Include top 5 for better context
        
        data_summary = "\n\n" + "="*80 + "\n"
        data_summary += "🚨 RANKING RESULTS DATA - YOU MUST USE THESE EXACT NUMBERS IN YOUR ANSWER 🚨\n"
        data_summary += "="*80 + "\n\n"
        
        data_summary += f"**Total methods ranked: {len(methods)}**\n\n"
        
        params = ranking_results.get('params', {})
        direction = 'higher' if params.get('bigbetter') else 'lower'
        direction_desc = 'higher values are better' if params.get('bigbetter') else 'lower values are better'
        data_summary += f"**Ranking direction: {direction}-is-better** ({direction_desc})\n"
        data_summary += f"**Bootstrap iterations (B): {params.get('B', 'N/A')}**\n"
        data_summary += f"**Random seed: {params.get('seed', 'N/A')}**\n\n"
        
        data_summary += "**TOP 5 RANKED METHODS (USE THESE EXACT NAMES AND NUMBERS):**\n\n"
        for method in top_5:
            name = method.get('name', 'Unknown')
            rank = method.get('rank', 'N/A')
            theta = method.get('theta_hat', 0)
            ci = method.get('ci_two_sided', [None, None])
            
            # Handle CI values - always format as integers (no decimals)
            if ci and ci[0] is not None and ci[1] is not None:
                if isinstance(ci[0], (int, float)) and isinstance(ci[1], (int, float)):
                    # Always format as integers (round to nearest integer)
                    ci_str = f"[{int(round(ci[0]))}, {int(round(ci[1]))}]"
                else:
                    ci_str = "N/A"
            else:
                ci_str = "N/A"
            
            data_summary += f"**Rank {rank}: {name}**\n"
            data_summary += f"  - Theta_hat (ranking score): {theta:.4f}\n"
            if ci_str != "N/A":
                data_summary += f"  - 95% Confidence Interval: {ci_str}\n"
            data_summary += "\n"
        
        # Calculate performance gap between #1 and #2
        if len(top_5) >= 2:
            top_theta = top_5[0].get('theta_hat', 0)
            second_theta = top_5[1].get('theta_hat', 0)
            gap = abs(top_theta - second_theta)
            gap_percent = (gap / max(abs(top_theta), abs(second_theta))) * 100 if max(abs(top_theta), abs(second_theta)) > 0 else 0
            data_summary += f"**Performance Gap Analysis:**\n"
            data_summary += f"  - Gap between Rank #1 ({top_5[0].get('name', 'Unknown')}) and Rank #2 ({top_5[1].get('name', 'Unknown')}): {gap:.4f} ({gap_percent:.1f}% relative difference)\n"
            data_summary += f"  - This indicates a {'significant' if gap > 0.05 else 'moderate' if gap > 0.02 else 'small'} performance difference\n\n"
        
        if len(sorted_methods) > 5:
            data_summary += f"**Additional methods:** {len(sorted_methods) - 5} more methods ranked (see full list in system context)\n\n"
        
        data_summary += "="*80 + "\n"
        data_summary += "**CRITICAL INSTRUCTION: Your answer MUST include the exact method names, ranks, and scores listed above. DO NOT give generic answers.**\n"
        data_summary += "="*80 + "\n"
        
        enhanced_user_message = user_message + data_summary
        print(f"DEBUG prepare_phase2_messages: Enhanced user message length: {len(enhanced_user_message)}")
        print(f"DEBUG prepare_phase2_messages: Data summary preview: {data_summary[:200]}...")
    else:
        enhanced_user_message = user_message
        print(f"DEBUG prepare_phase2_messages: WARNING - No ranking_results, using original user message only!")
    
    messages.append({
        'role': 'user',
        'content': enhanced_user_message
    })
    
    # Debug: Print final message structure
    print(f"DEBUG prepare_phase2_messages: Total messages: {len(messages)}")
    for i, msg in enumerate(messages):
        print(f"DEBUG prepare_phase2_messages: Message {i}: role={msg.get('role')}, content_length={len(msg.get('content', ''))}")
        if msg.get('role') == 'user':
            print(f"DEBUG prepare_phase2_messages: User message preview: {msg.get('content', '')[:300]}...")
    
    return messages


def manage_phase2_context(
    conversation_history: List[Dict],
    ranking_results: Optional[Dict[str, Any]] = None,
    max_history: int = 10
) -> List[Dict]:
    """
    Manage Phase 2 conversation context.
    
    Ensures the conversation history includes a summary of ranking results
    if one doesn't already exist.
    
    Args:
        conversation_history: Current conversation history
        ranking_results: Ranking results dictionary (optional)
        max_history: Maximum number of messages to keep
    
    Returns:
        Managed conversation history with summary if needed
    """
    # Keep recent conversation
    recent_history = conversation_history[-max_history:] if len(conversation_history) > max_history else conversation_history
    
    # Check if summary exists in history
    has_summary = any(
        'summary' in str(msg.get('content', '')).lower() or 
        'top' in str(msg.get('content', '')).lower() and 'ranked' in str(msg.get('content', '')).lower() or
        'analysis completed' in str(msg.get('content', '')).lower()
        for msg in recent_history
        if msg.get('role') == 'assistant'
    )
    
    # If no summary and results available, add summary as first assistant message
    if not has_summary and ranking_results:
        methods = ranking_results.get('methods', [])
        if methods:
            sorted_methods = sorted(methods, key=lambda x: x.get('rank', 999))
            top_3 = sorted_methods[:3]
            
            summary_lines = [
                f"Ranking analysis completed. {len(methods)} methods were ranked.",
                "Top 3 methods:"
            ]
            for method in top_3:
                theta = method.get('theta_hat', 0)
                summary_lines.append(
                    f"  {method.get('rank')}. {method.get('name')} (θ={theta:.4f})"
                )
            
            summary = "\n".join(summary_lines)
            recent_history.insert(0, {
                'role': 'assistant',
                'content': summary
            })
    
    return recent_history


def highlight_methods_in_response(content: str, methods: List[Dict]) -> str:
    """
    Highlight method names in Agent response for better readability.
    
    Args:
        content: The response content from Agent
        methods: List of method dictionaries from ranking results
    
    Returns:
        Content with method names highlighted
    """
    if not methods or not content:
        return content
    
    method_names = [m.get('name') for m in methods if m.get('name')]
    
    # Sort by length (longest first) to avoid partial matches
    method_names_sorted = sorted(method_names, key=len, reverse=True)
    
    for method_name in method_names_sorted:
        if method_name:
            # Use word boundaries to avoid partial matches
            # Escape special regex characters
            escaped_name = re.escape(method_name)
            # Create highlight pattern
            pattern = re.compile(r'\b' + escaped_name + r'\b', re.IGNORECASE)
            # Replace with highlighted version
            highlighted = f'<span style="background: #fff4e1; padding: 0.1rem 0.3rem; border-radius: 3px; font-weight: 600;">{method_name}</span>'
            content = pattern.sub(highlighted, content)
    
    return content


def extract_ranking_results_from_messages(messages: List[Dict]) -> Optional[Dict[str, Any]]:
    """
    Extract ranking results from message history.
    
    Looks for ranking results in system messages or tool results.
    
    Args:
        messages: List of message dictionaries
    
    Returns:
        Ranking results dictionary if found, None otherwise
    """
    import json
    
    # Search for ranking results in messages
    for msg in reversed(messages):  # Search from most recent
        # Check system messages for ranking results context
        if msg.get('role') == 'system':
            content = msg.get('content', '')
            if 'Ranking Results Context' in content:
                # Try to extract from context (this is a fallback)
                # In practice, ranking_results should be passed explicitly
                pass
        
        # Check tool results for get_results tool
        if msg.get('role') == 'tool' and msg.get('name') == 'get_results':
            content = msg.get('content', '{}')
            try:
                result = json.loads(content) if isinstance(content, str) else content
                if 'results' in result:
                    return result['results']
            except:
                pass
    
    return None


def is_phase2_request(messages: List[Dict], ranking_results: Optional[Dict[str, Any]] = None) -> bool:
    """
    Determine if this is a Phase 2 request (ranking results analysis).
    
    Args:
        messages: List of message dictionaries
        ranking_results: Optional ranking results dictionary
    
    Returns:
        True if this is a Phase 2 request, False otherwise
    """
    # Phase 2 keywords for detection
    phase2_keywords = [
        'ranking', 'results', 'method', 'compare', 'top', 'rank',
        'which method', 'what is the', 'tell me about', 'explain',
        'interpretation', 'analysis', 'theta', 'confidence'
    ]
    
    # Extract user message content (check all user messages, prioritize last one)
    # Strip HTML tags for keyword detection
    import re
    user_messages = [msg.get('content', '') for msg in messages if msg.get('role') == 'user']
    if user_messages:
        last_user_message = user_messages[-1]
        # Remove HTML tags for keyword detection
        text_content = re.sub(r'<[^>]+>', '', last_user_message).lower()
        has_phase2_keywords = any(keyword in text_content for keyword in phase2_keywords)
        print(f"DEBUG BACKEND is_phase2_request: last_user_message: {last_user_message[:100]}, text_content: {text_content[:100]}, has_phase2_keywords: {has_phase2_keywords}")
    else:
        has_phase2_keywords = False
        print(f"DEBUG BACKEND is_phase2_request: No user messages found")
    
    # If ranking_results is explicitly provided and has methods, it's Phase 2
    if ranking_results and isinstance(ranking_results, dict):
        print(f"DEBUG BACKEND is_phase2_request: ranking_results is dict, has methods: {bool(ranking_results.get('methods'))}, methods count: {len(ranking_results.get('methods', []))}")
        # Check if it has methods (strong indicator of Phase 2)
        if ranking_results.get('methods') and len(ranking_results.get('methods', [])) > 0:
            print(f"DEBUG BACKEND is_phase2_request: Returning True (has methods)")
            return True
        # Even if methods is empty/missing, if ranking_results exists and user asks Phase 2 questions, it's Phase 2
        if has_phase2_keywords:
            print(f"DEBUG BACKEND is_phase2_request: Returning True (has ranking_results and phase2 keywords)")
            return True
    else:
        print(f"DEBUG BACKEND is_phase2_request: ranking_results is None or not dict: {ranking_results is None}, type: {type(ranking_results)}")
    
    # Check if ranking results exist in message history
    extracted_results = extract_ranking_results_from_messages(messages)
    if extracted_results and extracted_results.get('methods'):
        return True
    
    # If user asks Phase 2 questions and we have ranking results (either passed or extracted), it's Phase 2
    if has_phase2_keywords and (extracted_results or ranking_results):
                    return True
    
    return False

