from urllib.parse import urljoin

from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied

from metaci.build.utils import paginate
from metaci.build.utils import view_queryset
from metaci.cumulusci.forms import OrgLockForm
from metaci.cumulusci.forms import OrgUnlockForm
from metaci.cumulusci.models import Org
from metaci.cumulusci.models import ScratchOrgInstance
from metaci.cumulusci.utils import get_connected_app
from metaci.plan.models import PlanRepository


@login_required
def org_detail(request, org_id):
    org = Org.objects.get_for_user_or_404(request.user, {"id": org_id})

    # Get builds
    query = {"org": org}
    builds = view_queryset(request, query)

    # Get ScratchOrgInstances
    instances = org.instances.filter(deleted=False) if org.scratch else []

    context = {"builds": builds, "org": org, "instances": instances}
    return render(request, "cumulusci/org_detail.html", context=context)


# not wired to urlconf; called by org_lock and org_unlock


def _org_lock_unlock(request, org_id, action):
    org = get_object_or_404(Org, id=org_id)
    if org.scratch:
        raise PermissionDenied("Scratch orgs may not be locked/unlocked")
    if action == "lock":
        form_class = OrgLockForm
        template = "cumulusci/org_lock.html"
    elif action == "unlock":
        form_class = OrgUnlockForm
        template = "cumulusci/org_unlock.html"
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            if request.POST["action"] == "Lock":
                org.lock()
            elif request.POST["action"] == "Unlock":
                org.unlock()
            return HttpResponseRedirect(org.get_absolute_url())
    else:
        form = form_class()
    return render(request, template, context={"form": form, "org": org})


@user_passes_test(lambda u: u.is_superuser)
def org_lock(request, org_id):
    return _org_lock_unlock(request, org_id, "lock")


@user_passes_test(lambda u: u.is_superuser)
def org_unlock(request, org_id):
    return _org_lock_unlock(request, org_id, "unlock")


@login_required
def org_login(request, org_id, instance_id=None):
    org = Org.objects.get_for_user_or_404(request.user, {"id": org_id})

    def get_org_config(org):
        org_config = org.get_org_config()

        org_config.refresh_oauth_token(keychain=None, connected_app=get_connected_app())
        return org_config

    # For non-scratch orgs, just log into the org
    if not org.scratch:
        org_config = get_org_config(org)
        return HttpResponseRedirect(org_config.start_url)

    # If an instance was selected, log into the org
    if instance_id:
        instance = get_object_or_404(ScratchOrgInstance, org_id=org_id, id=instance_id)

        # If the org is deleted, render the org deleted template
        if instance.deleted:
            raise Http404("Cannot log in: the org instance is already deleted")

        # Log into the scratch org
        session = instance.get_jwt_based_session()
        return HttpResponseRedirect(
            urljoin(
                str(session["instance_url"]),
                "secur/frontdoor.jsp?sid={}".format(session["access_token"]),
            )
        )

    raise Http404()


@login_required
def org_instance_delete(request, org_id, instance_id):
    instance = get_object_or_404(ScratchOrgInstance, org_id=org_id, id=instance_id)

    # Verify access
    try:
        org = Org.objects.for_user(request.user).get(id=org_id)
    except Org.DoesNotExist:
        raise PermissionDenied("You are not authorized to view this org")

    context = {"instance": instance}
    if instance.deleted:
        raise Http404("Cannot delete: this org instance is already deleted")

    instance.delete_org()
    return HttpResponseRedirect(instance.get_absolute_url())


@login_required
def org_instance_detail(request, org_id, instance_id):
    instance = get_object_or_404(ScratchOrgInstance, org_id=org_id, id=instance_id)

    # Verify access
    try:
        org = Org.objects.for_user(request.user).get(id=org_id)
    except Org.DoesNotExist:
        raise PermissionDenied("You are not authorized to view this org")

    # Get builds
    query = {"org_instance": instance}
    builds = view_queryset(request, query)

    context = {"builds": builds, "instance": instance}
    return render(request, "cumulusci/org_instance_detail.html", context=context)


@login_required
def org_list(request):
    query = {}
    repo = request.GET.get("repo")
    if repo:
        query["repo__name"] = repo
    scratch = request.GET.get("scratch")
    if scratch:
        query["scratch"] = scratch

    orgs = Org.objects.for_user(request.user).filter(**query)
    orgs = orgs.order_by("id")

    orgs = paginate(orgs, request)
    context = {"orgs": orgs}
    return render(request, "cumulusci/org_list.html", context=context)
