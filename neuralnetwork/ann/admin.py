from django.contrib import admin
from django.utils.html import format_html
import numpy as np
from .models import (
    CompanyProfile, Job, CandidateProfile, Application,
    ParsedResume, CandidateSkill, JobSkill, MatchScore, Interview
)


def deserialize_embedding(binary_data):
    """Deserialize binary embedding to numpy array."""
    if not binary_data:
        return None
    try:
        return np.frombuffer(binary_data, dtype=np.float32)
    except Exception:
        return None


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'user', 'industry', 'location', 'created_at']
    search_fields = ['company_name', 'user__username']


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'job_type', 'status', 'has_embedding', 'created_at']
    list_filter = ['status', 'job_type']
    search_fields = ['title', 'company', 'description']
    readonly_fields = ['embedding_info', 'embedding_preview']

    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'company', 'company_profile', 'location', 'job_type', 'status', 'category')
        }),
        ('Salary & Experience', {
            'fields': ('salary_min', 'salary_max', 'experience_min', 'experience_max')
        }),
        ('Description', {
            'fields': ('description', 'requirements', 'benefits', 'skills_required')
        }),
        ('Embedding Vector', {
            'fields': ('embedding_info', 'embedding_preview'),
            'classes': ('collapse',),
            'description': 'Semantic embedding for AI matching (384 dimensions)'
        }),
    )

    @admin.display(boolean=True, description='Embedding')
    def has_embedding(self, obj):
        return obj.embedding is not None and len(obj.embedding) > 0

    @admin.display(description='Embedding Status')
    def embedding_info(self, obj):
        vector = deserialize_embedding(obj.embedding)
        if vector is None:
            return format_html('<span style="color: red;">No embedding generated</span>')
        return format_html(
            '<span style="color: green;">Dimensions: {}</span><br>'
            '<span>Min: {:.4f} | Max: {:.4f} | Mean: {:.4f}</span>',
            vector.shape[0],
            float(vector.min()),
            float(vector.max()),
            float(vector.mean())
        )

    @admin.display(description='Vector Preview (first 20 values)')
    def embedding_preview(self, obj):
        vector = deserialize_embedding(obj.embedding)
        if vector is None:
            return "N/A"
        preview = ', '.join(f'{v:.4f}' for v in vector[:20])
        return format_html('<code style="font-size: 11px;">[{}...]</code>', preview)


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'location', 'experience_years', 'education_level', 'profile_strength', 'has_embedding']
    search_fields = ['user__username', 'full_name']
    list_filter = ['education_level']
    readonly_fields = ['embedding_status']

    @admin.display(boolean=True, description='Embedding')
    def has_embedding(self, obj):
        try:
            pr = obj.parsed_resume
            return pr.embedding is not None and len(pr.embedding) > 0
        except Exception:
            return False

    @admin.display(description='Embedding Status')
    def embedding_status(self, obj):
        try:
            pr = obj.parsed_resume
            vector = deserialize_embedding(pr.embedding)
            if vector is None:
                return format_html('<span style="color: red;">No embedding - upload resume to generate</span>')
            return format_html(
                '<span style="color: green;">Embedding exists ({} dims)</span><br>'
                'View details in <a href="/admin/ann/parsedresume/{}/change/">ParsedResume</a>',
                vector.shape[0], pr.id
            )
        except Exception:
            return format_html('<span style="color: orange;">No parsed resume yet</span>')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'job', 'status', 'applied_at']
    list_filter = ['status']
    search_fields = ['candidate__username', 'job__title']


@admin.register(ParsedResume)
class ParsedResumeAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'parsing_status', 'has_embedding', 'embedding_dims', 'parsed_at', 'created_at']
    list_filter = ['parsing_status']
    search_fields = ['candidate__user__username']
    readonly_fields = ['raw_text', 'cleaned_text', 'sections_json', 'embedding_info', 'embedding_preview', 'embedding_stats']

    fieldsets = (
        ('Status', {
            'fields': ('candidate', 'parsing_status', 'parsed_at', 'error_message')
        }),
        ('Extracted Text', {
            'fields': ('raw_text', 'cleaned_text'),
            'classes': ('collapse',)
        }),
        ('Sections', {
            'fields': ('sections_json',),
            'classes': ('collapse',)
        }),
        ('Embedding Vector', {
            'fields': ('embedding_info', 'embedding_stats', 'embedding_preview'),
            'description': 'Semantic embedding for AI matching (384 dimensions)'
        }),
    )

    @admin.display(boolean=True, description='Has Embedding')
    def has_embedding(self, obj):
        return obj.embedding is not None and len(obj.embedding) > 0

    @admin.display(description='Dims')
    def embedding_dims(self, obj):
        vector = deserialize_embedding(obj.embedding)
        if vector is None:
            return "-"
        return str(vector.shape[0])

    @admin.display(description='Embedding Status')
    def embedding_info(self, obj):
        vector = deserialize_embedding(obj.embedding)
        if vector is None:
            return format_html(
                '<span style="color: red; font-weight: bold;">No embedding generated</span><br>'
                '<span style="color: gray;">Re-upload resume or run: python manage.py shell</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">Embedding Ready</span><br>'
            '<span>Dimensions: {} | Size: {} bytes</span>',
            vector.shape[0],
            len(obj.embedding)
        )

    @admin.display(description='Vector Statistics')
    def embedding_stats(self, obj):
        vector = deserialize_embedding(obj.embedding)
        if vector is None:
            return "N/A"
        return format_html(
            '<table style="border-collapse: collapse;">'
            '<tr><td style="padding: 2px 10px;"><b>Min:</b></td><td>{:.6f}</td></tr>'
            '<tr><td style="padding: 2px 10px;"><b>Max:</b></td><td>{:.6f}</td></tr>'
            '<tr><td style="padding: 2px 10px;"><b>Mean:</b></td><td>{:.6f}</td></tr>'
            '<tr><td style="padding: 2px 10px;"><b>Std:</b></td><td>{:.6f}</td></tr>'
            '<tr><td style="padding: 2px 10px;"><b>Norm (L2):</b></td><td>{:.6f}</td></tr>'
            '</table>',
            float(vector.min()),
            float(vector.max()),
            float(vector.mean()),
            float(vector.std()),
            float(np.linalg.norm(vector))
        )

    @admin.display(description='Vector Preview (first 30 values)')
    def embedding_preview(self, obj):
        vector = deserialize_embedding(obj.embedding)
        if vector is None:
            return "N/A"
        preview = ', '.join(f'{v:.4f}' for v in vector[:30])
        return format_html(
            '<div style="background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 11px; word-break: break-all;">'
            '[{}...]<br><br>'
            '<span style="color: gray;">Showing 30 of {} dimensions</span>'
            '</div>',
            preview,
            vector.shape[0]
        )


@admin.register(CandidateSkill)
class CandidateSkillAdmin(admin.ModelAdmin):
    list_display = ['skill_text', 'candidate', 'category', 'proficiency_level', 'confidence_score', 'source']
    list_filter = ['category', 'proficiency_level', 'source']
    search_fields = ['skill_text', 'candidate__user__username']


@admin.register(JobSkill)
class JobSkillAdmin(admin.ModelAdmin):
    list_display = ['skill_text', 'job', 'category', 'importance']
    list_filter = ['category', 'importance']
    search_fields = ['skill_text', 'job__title']


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['application', 'scheduled_date', 'interview_type', 'status', 'interviewer', 'created_at']
    list_filter = ['status', 'interview_type']
    search_fields = ['application__candidate__username', 'application__job__title', 'interviewer']


@admin.register(MatchScore)
class MatchScoreAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'job', 'overall_score', 'skill_match_score', 'semantic_similarity', 'is_valid']
    list_filter = ['is_valid']
    search_fields = ['candidate__user__username', 'job__title']
    readonly_fields = ['matched_skills', 'missing_skills', 'suggestions', 'score_breakdown']

    fieldsets = (
        ('Match', {
            'fields': ('candidate', 'job', 'overall_score', 'is_valid')
        }),
        ('Score Breakdown', {
            'fields': ('score_breakdown', 'semantic_similarity', 'skill_match_score', 'experience_match_score', 'education_match_score', 'profile_completeness_score')
        }),
        ('Skills Analysis', {
            'fields': ('matched_skills', 'missing_skills'),
            'classes': ('collapse',)
        }),
        ('Suggestions', {
            'fields': ('suggestions',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Visual Breakdown')
    def score_breakdown(self, obj):
        def bar(label, value, weight, color):
            weighted = value * weight
            return f'''
                <tr>
                    <td style="padding: 3px 10px;">{label}</td>
                    <td style="padding: 3px 10px; width: 200px;">
                        <div style="background: #eee; border-radius: 3px; height: 16px;">
                            <div style="background: {color}; width: {value}%; height: 100%; border-radius: 3px;"></div>
                        </div>
                    </td>
                    <td style="padding: 3px 10px;">{value:.1f}%</td>
                    <td style="padding: 3px 10px; color: gray;">x{weight}</td>
                    <td style="padding: 3px 10px; font-weight: bold;">{weighted:.1f}</td>
                </tr>
            '''

        html = '<table style="border-collapse: collapse;">'
        html += '<tr style="background: #f0f0f0;"><th style="padding: 5px;">Component</th><th>Score</th><th>Value</th><th>Weight</th><th>Weighted</th></tr>'
        html += bar('Semantic', obj.semantic_similarity, 0.25, '#3498db')
        html += bar('Skills', obj.skill_match_score, 0.35, '#2ecc71')
        html += bar('Experience', obj.experience_match_score, 0.20, '#9b59b6')
        html += bar('Education', obj.education_match_score, 0.10, '#f39c12')
        html += bar('Profile', obj.profile_completeness_score, 0.10, '#e74c3c')
        html += f'<tr style="background: #f0f0f0;"><td colspan="4" style="padding: 5px; text-align: right;"><b>Total:</b></td><td style="padding: 5px;"><b>{obj.overall_score:.1f}%</b></td></tr>'
        html += '</table>'
        return format_html(html)
