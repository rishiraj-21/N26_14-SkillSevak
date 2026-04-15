"""
Signals for SkillSevak

Handles automatic CandidateProfile creation for social auth users.
"""

import logging

logger = logging.getLogger(__name__)



def handle_social_login(sender, request, sociallogin, **kwargs):
    """
    Handle social login (Google) - extract additional user info.

    Connected to allauth's social_account_added signal.
    """
    user = sociallogin.user
    account = sociallogin.account

    # Extract data from Google
    extra_data = account.extra_data

    # Update user profile with Google data
    if extra_data:
        try:
            from ann.models import CandidateProfile

            profile, created = CandidateProfile.objects.get_or_create(user=user)

            # Update name if not set
            if not profile.full_name:
                profile.full_name = extra_data.get('name', '')

            profile.save()
            logger.info(f"Updated profile for Google user: {user.username}")

        except Exception as e:
            logger.warning(f"Failed to update profile from Google data: {e}")


# Connect the social login signal
try:
    from allauth.socialaccount.signals import social_account_added
    social_account_added.connect(handle_social_login)
except ImportError:
    # allauth not installed
    pass
