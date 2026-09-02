from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .audit_integrity import create_checkpoint, verify_latest_checkpoint
from .rbac import GovernancePermission


@api_view(["GET", "POST"])
@permission_classes([GovernancePermission])
def integrity(request):
    if request.method == "POST":
        checkpoint = create_checkpoint(request.user)
        result = verify_latest_checkpoint(request.user)
        result["created_checkpoint_event_id"] = checkpoint.id
        return Response(result, status=201)
    return Response(verify_latest_checkpoint(request.user))
