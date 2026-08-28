from apps.api.app.modules.reports.infrastructure.orm import InterviewReportORM


class PDFReportGenerator:
    """
    Immutable Report PDF Generator Service (ADR 050).
    Renders formatted PDF report bytes from an immutable InterviewReportORM record snapshot.
    """
    @staticmethod
    def generate_pdf_bytes(report: InterviewReportORM) -> bytes:
        # Generate formatted PDF document layout text/bytes
        header = "%PDF-1.4\n% InterviewIQ Immutable Technical Interview Evaluation Report\n"
        header += f"% Report ID: {report.id}\n"
        header += f"% Session ID: {report.interview_session_id}\n"
        header += f"% Version: v{report.report_version} (Scoring Engine: {report.scoring_version})\n"
        header += f"% Seniority: {report.seniority_assessment}\n"
        header += f"% Overall Score: {report.overall_score:.2f}/10.0\n"
        header += f"% Hiring Signal: {report.hiring_signal}\n"

        content = "\n1 0 obj\n<< /Title (InterviewIQ Report) /Author (InterviewIQ Engine) >>\nendobj\n"
        content += f"2 0 obj\n<< /Length {len(report.executive_summary)} >>\nstream\n"
        content += f"Executive Summary:\n{report.executive_summary}\n"
        content += f"\nKey Strengths: {', '.join(report.top_strengths.get('strengths', []))}\n"
        content += f"Growth Areas: {', '.join(report.growth_areas.get('growth_areas', []))}\n"
        content += "\nendstream\nendobj\n"

        trailer = "xref\n0 3\n0000000000 65535 f \ntrailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n180\n%%EOF"

        full_document = (header + content + trailer).encode("utf-8")
        return full_document
