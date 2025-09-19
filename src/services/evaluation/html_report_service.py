"""
HTML Report Service - Generates beautiful HTML reports from test results
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from src.utils.logger import Logger
from src.models.types import PATHS

class HTMLReportService:
    """Service for generating HTML reports from test results"""
    
    @staticmethod
    def generate_html_report(test_result: Dict, output_dir: str = None) -> Dict:
        """Generate HTML report from a single test result"""
        try:
            if output_dir is None:
                output_dir = PATHS.TEST_RESULTS / "html_reports"
            
            # Ensure output directory exists
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{test_result.get('test_id', 'unknown')}_{timestamp}.html"
            filepath = Path(output_dir) / filename
            
            # Generate HTML content
            html_content = HTMLReportService._generate_html_content(test_result)
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            Logger.success(f"✅ HTML report generated: {filepath}")
            
            return {
                'success': True,
                'filepath': str(filepath),
                'filename': filename
            }
            
        except Exception as error:
            Logger.error(f"❌ Failed to generate HTML report: {error}")
            return {
                'success': False,
                'error': str(error)
            }
    
    @staticmethod
    def _generate_html_content(test_result: Dict) -> str:
        """Generate the HTML content for the report"""
        
        # Extract data
        test_id = test_result.get('test_id', 'Unknown')
        scenario = test_result.get('scenario', 'Unknown Scenario')
        result = test_result.get('scenario_result', 'unknown').upper()
        transcript = test_result.get('transcript', '')
        golden_transcript = test_result.get('golden_transcript', '')
        evaluation_details = test_result.get('evaluation_details', {})
        metadata = test_result.get('metadata', {})
        
        # Determine result color
        result_color = {
            'PASS': '#28a745',
            'FAIL': '#dc3545',
            'UNKNOWN': '#6c757d'
        }.get(result, '#6c757d')
        
        # Format timestamp
        timestamp = metadata.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                formatted_time = timestamp
        else:
            formatted_time = 'Unknown'
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - {test_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .result-badge {{
            display: inline-block;
            background: {result_color};
            color: white;
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1em;
            margin: 20px 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .section {{
            margin-bottom: 40px;
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            border-left: 5px solid #667eea;
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .info-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .info-card h3 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .info-card p {{
            color: #666;
            font-size: 0.95em;
        }}
        
        .transcript-container {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .transcript-header {{
            background: #667eea;
            color: white;
            padding: 15px 20px;
            font-weight: bold;
        }}
        
        .transcript-content {{
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.8;
            background: #f8f9fa;
        }}
        
        .evaluation-details {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .evaluation-item {{
            margin-bottom: 20px;
        }}
        
        .evaluation-item h4 {{
            color: #667eea;
            margin-bottom: 8px;
            font-size: 1.1em;
        }}
        
        .evaluation-item p {{
            color: #666;
            line-height: 1.6;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e9ecef;
        }}
        
        .highlight {{
            background: #fff3cd;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        
        .error {{
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        
        .success {{
            background: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
                border-radius: 10px;
            }}
            
            .header {{
                padding: 20px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .content {{
                padding: 20px;
            }}
            
            .info-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Test Report</h1>
            <div class="subtitle">AgenticAI Testing Suite</div>
            <div class="result-badge">{result}</div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📋 Test Information</h2>
                <div class="info-grid">
                    <div class="info-card">
                        <h3>Test ID</h3>
                        <p>{test_id}</p>
                    </div>
                    <div class="info-card">
                        <h3>Scenario</h3>
                        <p>{scenario}</p>
                    </div>
                    <div class="info-card">
                        <h3>Result</h3>
                        <p style="color: {result_color}; font-weight: bold;">{result}</p>
                    </div>
                    <div class="info-card">
                        <h3>Timestamp</h3>
                        <p>{formatted_time}</p>
                    </div>
                    <div class="info-card">
                        <h3>Duration</h3>
                        <p>{metadata.get('duration_ms', 0)} ms</p>
                    </div>
                    <div class="info-card">
                        <h3>Audio Files Sent</h3>
                        <p>{metadata.get('audio_files_sent', 0)}</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>📝 Conversation Transcript</h2>
                <div class="transcript-container">
                    <div class="transcript-header">
                        Actual Conversation
                    </div>
                    <div class="transcript-content">
                        {HTMLReportService._format_transcript(transcript)}
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>🎯 Golden Transcript</h2>
                <div class="transcript-container">
                    <div class="transcript-header">
                        Expected Conversation
                    </div>
                    <div class="transcript-content">
                        {HTMLReportService._format_transcript(golden_transcript)}
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>📊 Evaluation Details</h2>
                <div class="evaluation-details">
                    {HTMLReportService._format_evaluation_details(evaluation_details)}
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by AgenticAI Testing Suite on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    @staticmethod
    def _format_transcript(transcript: str) -> str:
        """Format transcript for HTML display"""
        if not transcript:
            return '<em>No transcript available</em>'
        
        # First, normalize line breaks - split on both \n and common patterns
        # Handle cases where Agent: and User: are on the same line
        import re
        
        # Split the transcript into Agent and User segments
        segments = re.split(r'(Agent:|User:)', transcript)
        
        formatted_lines = []
        current_speaker = None
        current_text = ""
        
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
                
            if segment == 'Agent:':
                # If we have accumulated text, add it first
                if current_text and current_speaker:
                    formatted_lines.append(f'<div style="color: {"#667eea" if current_speaker == "Agent" else "#28a745"}; font-weight: bold; margin-bottom: 8px;">{current_speaker}: {current_text}</div>')
                
                current_speaker = "Agent"
                current_text = ""
            elif segment == 'User:':
                # If we have accumulated text, add it first
                if current_text and current_speaker:
                    formatted_lines.append(f'<div style="color: {"#667eea" if current_speaker == "Agent" else "#28a745"}; font-weight: bold; margin-bottom: 8px;">{current_speaker}: {current_text}</div>')
                
                current_speaker = "User"
                current_text = ""
            else:
                # This is the text content
                current_text = segment.strip()
        
        # Add the last segment
        if current_text and current_speaker:
            formatted_lines.append(f'<div style="color: {"#667eea" if current_speaker == "Agent" else "#28a745"}; font-weight: bold; margin-bottom: 8px;">{current_speaker}: {current_text}</div>')
        
        return ''.join(formatted_lines)
    
    @staticmethod
    def _format_evaluation_details(evaluation_details: Dict) -> str:
        """Format evaluation details for HTML display"""
        if not evaluation_details:
            return '<em>No evaluation details available</em>'
        
        html_parts = []
        
        if 'failure_reason' in evaluation_details:
            html_parts.append(f'''
                <div class="evaluation-item">
                    <h4>❌ Failure Reason</h4>
                    <div class="error">{evaluation_details['failure_reason']}</div>
                </div>
            ''')
        
        if 'what_went_well' in evaluation_details:
            html_parts.append(f'''
                <div class="evaluation-item">
                    <h4>✅ What Went Well</h4>
                    <div class="success">{evaluation_details['what_went_well']}</div>
                </div>
            ''')
        
        if 'what_to_improve' in evaluation_details:
            html_parts.append(f'''
                <div class="evaluation-item">
                    <h4>🔧 What to Improve</h4>
                    <p>{evaluation_details['what_to_improve']}</p>
                </div>
            ''')
        
        return ''.join(html_parts) if html_parts else '<em>No evaluation details available</em>'
    
    @staticmethod
    def generate_html_report_from_json_file(json_filepath: str, output_dir: str = None) -> Dict:
        """Generate HTML report from a JSON file"""
        try:
            # Read JSON file
            with open(json_filepath, 'r', encoding='utf-8') as f:
                test_result = json.load(f)
            
            # Generate HTML report
            return HTMLReportService.generate_html_report(test_result, output_dir)
            
        except Exception as error:
            Logger.error(f"❌ Failed to generate HTML report from JSON file: {error}")
            return {
                'success': False,
                'error': str(error)
            } 