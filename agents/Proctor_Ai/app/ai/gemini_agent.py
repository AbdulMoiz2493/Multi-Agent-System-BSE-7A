"""
Gemini Flash Agent for Daily Revision Proctor
Uses Google's Gemini model to analyze student data and provide intelligent recommendations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent

from app.core.config import settings
from app.schemas.ai import (
    SupervisorAgentRequest,
    SupervisorAgentResponse,
    SupervisorAnalysisSummary,
    SupervisorReminderScheduleItem,
    SupervisorPerformanceAlert,
    SupervisorReportSummary
)
from app.ai.tools import AGENT_TOOLS, get_student_study_sessions, calculate_consistency_score
from app.ai.insights_service import InsightsService
from app.ai.reminder_service import ReminderService


class GeminiRevisionAgent:
    """
    Daily Revision Proctor AI Agent powered by Gemini Flash
    Analyzes student study patterns and provides personalized recommendations
    """
    
    SYSTEM_PROMPT = """You are the Daily Revision Proctor AI Agent, an intelligent academic support system.

Your role is to:
1. Monitor student learning activities and study patterns
2. Generate personalized study recommendations
3. Identify areas needing improvement
4. Create adaptive reminder schedules
5. Provide performance alerts and insights

You have access to tools that can query the student database. Use them to fill in missing information.

When analyzing a student:
- Check their study history using get_student_study_sessions
- Calculate their consistency using calculate_consistency_score
- Identify neglected subjects
- Provide actionable, specific recommendations
- Be encouraging but honest about areas needing improvement

CRITICAL: You must return your analysis in a structured format that matches the SupervisorAgentResponse schema.
"""
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """Initialize the Gemini agent"""
        api_key = gemini_api_key or getattr(settings, 'GEMINI_API_KEY', None)
        
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Please set it in your .env file or pass it to the constructor."
            )
        
        # Initialize Gemini model
    
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.7,
            max_output_tokens=4096,
        )
        
        # Create agent with tools
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        self.agent = create_tool_calling_agent(self.llm, AGENT_TOOLS, prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=AGENT_TOOLS,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )
    
    def analyze_student(
        self, 
        request: SupervisorAgentRequest, 
        db: Session
    ) -> SupervisorAgentResponse:
        """
        Main analysis method that processes supervisor request and returns structured response
        """
        student_id = request.student_id
        
        # Step 1: Gather data from database using tools
        db_sessions = get_student_study_sessions.invoke({"student_id": student_id, "days": 30})
        
        # Step 2: Merge with provided activity log
        all_sessions = []
        if db_sessions.get("success"):
            all_sessions.extend(db_sessions.get("sessions", []))
        
        # Add activity log from supervisor
        for log in request.activity_log:
            all_sessions.append({
                "date": log.date,
                "subject": log.subject,
                "hours": log.hours,
                "status": log.status
            })
        
        # Calculate consistency from merged data
        if all_sessions:
            from datetime import datetime
            unique_dates = set()
            date_objects = []
            
            for s in all_sessions:
                date_val = s.get("date")
                if date_val:
                    # Handle both string dates and datetime objects
                    if isinstance(date_val, str):
                        unique_dates.add(date_val)
                        try:
                            date_objects.append(datetime.strptime(date_val, "%Y-%m-%d"))
                        except:
                            pass
                    else:
                        date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, 'strftime') else str(date_val)
                        unique_dates.add(date_str)
                        date_objects.append(date_val if hasattr(date_val, 'strftime') else datetime.strptime(date_str, "%Y-%m-%d"))
            
            # Calculate days_analyzed based on actual date range (more fair)
            if date_objects and len(date_objects) > 1:
                days_analyzed = (max(date_objects) - min(date_objects)).days + 1
                # But use minimum of 7 days to avoid inflated scores for 1-2 day spans
                days_analyzed = max(days_analyzed, 7)
            else:
                days_analyzed = 7  # Single day = judge over a week
            
            consistency_score = round((len(unique_dates) / days_analyzed) * 100, 2)
        else:
            consistency_score = 0
        
        # Step 3: Calculate analysis summary
        total_hours = sum(s.get("hours", 0) for s in all_sessions)
        
        # Calculate completion rate from all sessions (merged)
        sessions_with_status = [s for s in all_sessions if s.get("status")]
        if sessions_with_status:
            completed = sum(1 for s in sessions_with_status if s.get("status") == "completed")
            completion_rate = f"{int((completed / len(sessions_with_status)) * 100)}%"
        else:
            completion_rate = "N/A"
        
        # Subject analysis
        subject_hours = {}
        for session in all_sessions:
            subject = session.get("subject", "Unknown")
            subject_hours[subject] = subject_hours.get(subject, 0) + session.get("hours", 0)
        
        most_active = max(subject_hours.items(), key=lambda x: x[1])[0] if subject_hours else "N/A"
        
        # Find least active from profile subjects (if provided)
        profile_subjects = request.profile.get("subjects", [])
        least_active = None
        if profile_subjects:
            for subject in profile_subjects:
                if subject not in subject_hours or subject_hours[subject] < 1:
                    least_active = subject
                    break
        else:
            # If no profile subjects provided, find least active from actual sessions
            if len(subject_hours) > 1:
                least_active = min(subject_hours.items(), key=lambda x: x[1])[0]
        
        analysis_summary = SupervisorAnalysisSummary(
            total_study_hours=round(total_hours, 1),
            average_completion_rate=completion_rate,
            most_active_subject=most_active,
            least_active_subject=least_active
        )
        
        # Step 4: Generate AI-powered recommendations using the agent
        agent_input = f"""
Analyze this student's performance and provide 3-5 specific, actionable recommendations.

Student ID: {student_id}
Profile: {request.profile}
Total Study Hours: {total_hours}
Completion Rate: {completion_rate}
Most Active Subject: {most_active}
Least Active Subject: {least_active}
Consistency Score: {consistency_score}%

Recent Activity:
{self._format_activity_log(request.activity_log)}

User Feedback:
- Reminder Effectiveness: {request.user_feedback.reminder_effectiveness}/5
- Motivation Level: {request.user_feedback.motivation_level}

IMPORTANT: Return ONLY a simple numbered list of recommendations. Do NOT wrap in JSON or code blocks.

Example format:
1. Increase study frequency to at least 4 days per week
2. Balance time between all subjects
3. Set daily reminders at preferred times
"""
        
        try:
            agent_response = self.agent_executor.invoke({"input": agent_input})
            recommendations_text = agent_response.get("output", "")
            recommendations = self._parse_recommendations(recommendations_text)
        except Exception as e:
            # Fallback to rule-based recommendations
            recommendations = self._generate_fallback_recommendations(
                request, most_active, least_active, consistency_score
            )
        
        # Step 5: Generate reminder schedule
        reminder_schedule = self._create_reminder_schedule(
            request.study_schedule.preferred_times
        )
        
        # Step 6: Generate performance alerts
        alerts = self._generate_performance_alerts(
            request, consistency_score
        )
        
        # Step 7: Create report summary
        report_summary = self._create_report_summary(
            request, consistency_score, total_hours
        )
        
        return SupervisorAgentResponse(
            student_id=student_id,
            analysis_summary=analysis_summary,
            recommendations=recommendations,
            reminder_schedule=reminder_schedule,
            performance_alerts=alerts,
            report_summary=report_summary
        )
    
    def _format_activity_log(self, activity_log: List) -> str:
        """Format activity log for agent input"""
        if not activity_log:
            return "No recent activity"
        
        lines = []
        for log in activity_log[-10:]:  # Last 10 entries
            lines.append(f"- {log.date}: {log.subject} ({log.hours}h) - {log.status}")
        return "\n".join(lines)
    
    def _parse_recommendations(self, text: str) -> List[str]:
        """Parse recommendations from agent output"""
        import re
        import json
        
        recommendations = []
        
        # Try to extract JSON if present
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict) and 'recommendations' in data:
                    recommendations = data['recommendations']
                    return recommendations[:5]
            except:
                pass
        
        # Try to find JSON without code blocks
        try:
            # Look for { ... } pattern
            json_match = re.search(r'\{.*"recommendations".*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                if isinstance(data, dict) and 'recommendations' in data:
                    recommendations = data['recommendations']
                    return recommendations[:5]
        except:
            pass
        
        # Fallback: Parse numbered/bulleted list
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            # Look for numbered or bulleted recommendations
            if line and len(line) > 15:
                # Match patterns like "1.", "1)", "-", "•", "**"
                if re.match(r'^[\d]+[\.\)]\s+', line) or line.startswith(('-', '•', '*')):
                    clean_line = re.sub(r'^[\d]+[\.\)]\s+', '', line)
                    clean_line = clean_line.lstrip('-•*) ').strip()
                    clean_line = clean_line.replace('**', '')
                    if len(clean_line) > 15:
                        recommendations.append(clean_line)
        
        # Last resort: split by periods
        if not recommendations:
            sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 25]
            recommendations = sentences[:5]
        
        return recommendations[:5]
    
    def _generate_fallback_recommendations(
        self, 
        request: SupervisorAgentRequest,
        most_active: str,
        least_active: Optional[str],
        consistency_score: float
    ) -> List[str]:
        """Generate rule-based recommendations as fallback"""
        recommendations = []
        
        # Consistency recommendation
        if consistency_score < 50:
            recommendations.append("Establish a more consistent daily study routine to improve retention.")
        elif consistency_score > 80:
            recommendations.append("Excellent consistency! Maintain your current study schedule.")
        
        # Subject balance
        if least_active:
            recommendations.append(f"Add one more revision session for {least_active}.")
        if most_active and most_active != "N/A":
            recommendations.append(f"Continue current schedule for {most_active}.")
        
        # Completion rate
        partial_count = sum(1 for log in request.activity_log if log.status == "partial")
        if partial_count > len(request.activity_log) * 0.3:
            recommendations.append("Focus on completing full study sessions rather than partial ones.")
        
        return recommendations[:5]
    
    def _create_reminder_schedule(self, preferred_times: List[str]) -> List[SupervisorReminderScheduleItem]:
        """Create weekly reminder schedule"""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        schedule = []
        
        for i, day in enumerate(days):
            if i < len(preferred_times):
                time = preferred_times[i % len(preferred_times)]
            else:
                time = preferred_times[0] if preferred_times else "7:00 PM"
            
            schedule.append(SupervisorReminderScheduleItem(day=day, time=time))
        
        return schedule
    
    def _generate_performance_alerts(
        self, 
        request: SupervisorAgentRequest,
        consistency_score: float
    ) -> List[SupervisorPerformanceAlert]:
        """Generate performance alerts based on patterns"""
        alerts = []
        
        # Check for missed sessions
        if request.activity_log:
            recent_statuses = [log.status for log in request.activity_log[-5:]]
            missed_count = sum(1 for s in recent_statuses if s in ["partial", "missed"])
            
            if missed_count >= 3:
                alerts.append(SupervisorPerformanceAlert(
                    type="critical",
                    message=f"Missed {missed_count} consecutive study sessions."
                ))
            elif missed_count >= 2:
                alerts.append(SupervisorPerformanceAlert(
                    type="warning",
                    message=f"Missed {missed_count} recent study sessions."
                ))
        
        # Consistency alerts (only if there's actual data to judge)
        # Don't penalize students with few sessions if they're all recent
        if consistency_score > 0:  # Has some data
            if consistency_score < 20:  # Less than 6 days in a month
                alerts.append(SupervisorPerformanceAlert(
                    type="critical",
                    message="Very low consistency score. Immediate attention needed."
                ))
            elif consistency_score < 40:  # Less than 12 days in a month
                alerts.append(SupervisorPerformanceAlert(
                    type="warning",
                    message="Below-average consistency. Consider setting reminders."
                ))
        
        # Positive feedback
        if not alerts:
            alerts.append(SupervisorPerformanceAlert(
                type="success",
                message="Student is performing well with consistent study habits."
            ))
        
        return alerts
    
    def _create_report_summary(
        self, 
        request: SupervisorAgentRequest,
        consistency_score: float,
        total_hours: float
    ) -> SupervisorReportSummary:
        """Create weekly report summary"""
        # Determine week range
        if request.activity_log:
            try:
                dates = [datetime.strptime(log.date, "%Y-%m-%d") for log in request.activity_log]
                start_date = min(dates)
                end_date = max(dates)
                week_str = f"{start_date.strftime('%b %d')}–{end_date.strftime('%b %d')}"
            except:
                week_str = "Current Week"
        else:
            week_str = "Current Week"
        
        # Determine engagement level
        if consistency_score >= 70 and total_hours >= 10:
            engagement_level = "High"
        elif consistency_score >= 40 and total_hours >= 5:
            engagement_level = "Medium"
        else:
            engagement_level = "Low"
        
        return SupervisorReportSummary(
            week=week_str,
            consistency_score=int(consistency_score),
            engagement_level=engagement_level
        )

