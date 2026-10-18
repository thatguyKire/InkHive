"""The shared demo accounts and the sample class they start with."""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.authentication.models import CustomUser
from modules.chat.models import ChatRoom, Message
from modules.notifications.models import Notification
from modules.session.models import Session, Participant, generate_session_code
from modules.settings_app.account import delete_user_account

TEACHER = "demo_teacher"
STUDENT = "demo_student"
CLASSMATE = "demo_classmate"
ACCOUNTS = (  # username, role, student ID
    (TEACHER, "teacher", None),
    (STUDENT, "student", "DEMO-0001"),
    (CLASSMATE, "student", "DEMO-0002"),
)

# Everything the demo accounts made is wiped when the demo is older than this.
RESET_AFTER = timedelta(hours=24)


def ensure_demo_data():
    """Create the demo accounts and sample class, starting over once a day."""
    teacher = CustomUser.objects.filter(username=TEACHER, is_demo=True).first()
    if teacher and timezone.now() - teacher.date_joined < RESET_AFTER:
        return
    if teacher:
        reset_demo_data()
    else:
        _create()


def reset_demo_data():
    """Delete the demo accounts with everything they made (files too), then re-create them."""
    for user in CustomUser.objects.filter(is_demo=True):
        delete_user_account(user)
    _create()


def _create():
    try:
        with transaction.atomic():
            users = {}
            for username, role, student_id in ACCOUNTS:
                user = CustomUser(username=username, email=f"{username}@demo.invalid", role=role,
                                  student_id=student_id, is_demo=True)
                user.set_unusable_password()  # only the demo buttons can sign in
                user.accept_terms()
                user.save()
                users[username] = user

            session = Session.objects.create(title="Welcome to the demo class", created_by=users[TEACHER],
                                             code=generate_session_code())
            Participant.objects.create(user=users[STUDENT], session=session, can_draw=True)
            Participant.objects.create(user=users[CLASSMATE], session=session)
            room = ChatRoom.objects.create(name=f"Session {session.id} Chat", session=session)
            Message.objects.create(room=room, sender=users[TEACHER],
                                   content="Welcome! Draw on the board, upload a picture, or ask a question here.")
            for username in (STUDENT, CLASSMATE):
                Notification.objects.create(recipient=users[username], session=session,
                                            content="Welcome to the demo class! The board is open, so try drawing.")
    except IntegrityError:
        pass  # another request created them at the same moment
