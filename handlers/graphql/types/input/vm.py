from typing import Optional

import graphene

from authentication import with_authentication, with_default_authentication, return_if_access_is_not_granted
from handlers.graphql.graphql_handler import ContextProtocol
from handlers.graphql.mutation_utils.base import MutationMethod, MutationHelper
from handlers.graphql.resolvers import with_connection
from handlers.graphql.types.objecttype import InputObjectType
from xenadapter.vm import VM
from handlers.graphql.types.vm import DomainType


class VMInput(InputObjectType):
    ref = graphene.InputField(graphene.ID, required=True, description="VM ref")
    name_label = graphene.InputField(graphene.String, description="VM human-readable name")
    name_description = graphene.InputField(graphene.String, description="VM human-readable description")
    domain_type = graphene.InputField(DomainType, description="VM domain type: 'pv', 'hvm', 'pv_in_pvh'")

def set_name_label(ctx : ContextProtocol, vm : VM, changes : VMInput):
    if changes.name_label is not None:
        vm.set_name_label(changes.name_label)


def set_name_description(ctx: ContextProtocol, vm: VM, changes: VMInput):
    if changes.name_description is not None:
        vm.set_name_description(changes.name_description)

def set_domain_type(ctx: ContextProtocol, vm: VM, changes: VMInput):
    if changes.domain_type is not None:
        vm.set_domain_type(changes.domain_type)


class VMMutation(graphene.Mutation):
    '''
    This class represents synchronous mutations for VM, i.e. you can change name_label, name_description, etc.
    '''
    granted = graphene.Field(graphene.Boolean, required=True)
    reason = graphene.Field(graphene.String)

    class Arguments:
        vm = graphene.Argument(VMInput, description="VM to change", required=True)


    @staticmethod
    @with_default_authentication
    @with_connection
    def mutate(root, info, vm):
        ctx : ContextProtocol = info.context

        mutable = VM(ctx.xen, vm.ref)

        mutations = [
            MutationMethod(func=set_name_label, access_action=VM.Actions.rename),
            MutationMethod(func=set_name_description, access_action=VM.Actions.rename),
            MutationMethod(func=set_domain_type, access_action=VM.Actions.change_domain_type)
        ]

        def reason(method: MutationMethod):
            return f"Action {method.access_action} is required to perform mutation on VM {mutable.ref}"

        helper = MutationHelper(mutations, ctx, mutable)
        granted, method = helper.perform_mutations(vm)
        if not granted:
            return VMMutation(granted=False, reason=reason(method))

        return VMMutation(granted=True)


class VMStartInput(InputObjectType):
    paused = graphene.InputField(graphene.Boolean, default_value=False, description="Should this VM be started and immidiately paused")
    # todo Implement Host field
    force = graphene.InputField(graphene.Boolean, default_value=False, description="Should this VM be started forcibly")


class VMStartMutation(graphene.Mutation):
    taskId = graphene.ID(required=False, description="Start task ID")
    granted = graphene.Boolean(required=True, description="Shows if access to start is granted")
    reason = graphene.String()

    class Arguments:
        ref = graphene.ID(required=True)
        options = graphene.Argument(VMStartInput)

    @staticmethod
    @with_authentication(access_class=VM, access_action=VM.Actions.start)
    @return_if_access_is_not_granted([("VM", "ref", VM.Actions.start)])
    def mutate(root, info, ref, options : VMStartInput = None, **kwargs):
        ctx :ContextProtocol = info.context
        vm = kwargs['VM']
        paused = options.paused if options else False
        force = options.force if options else False
        return VMStartMutation(granted=True, taskId=vm.async_start(paused, force))


class ShutdownForce(graphene.Enum):
    HARD = 1
    CLEAN = 2


class VMShutdownMutation(graphene.Mutation):
    taskId = graphene.ID(required=False, description="Shutdown task ID")
    granted = graphene.Boolean(required=True, description="Shows if access to shutdown is granted")

    class Arguments:
        ref = graphene.ID(required=True)
        force = graphene.Argument(ShutdownForce, description="Force shutdown in a hard or clean way")

    @staticmethod
    def mutate(root, info, ref, force: Optional[ShutdownForce] = None):
        if force is None:
            access_action = VM.Actions.shutdown
            method = 'async_shutdown'
        elif force == ShutdownForce.HARD:
            access_action = VM.Actions.hard_shutdown
            method = 'async_hard_shutdown'
        elif force == ShutdownForce.CLEAN:
            access_action = VM.Actions.clean_shutdown
            method = 'async_clean_shutdown'

        @with_authentication(access_class=VM, access_action=access_action)
        def get_vm(*args, **kwargs):
            return kwargs['VM']

        vm = get_vm(root, info, ref, force)
        if not vm:
            return VMShutdownMutation(granted=False)
        call = getattr(vm, method)
        return VMShutdownMutation(taskId=call(), granted=True)


class VMRebootMutation(graphene.Mutation):
    taskId = graphene.ID(required=False, description="Reboot task ID")
    granted = graphene.Boolean(required=True, description="Shows if access to reboot is granted")
    class Arguments:
        ref = graphene.ID(required=True)
        force = graphene.Argument(ShutdownForce, description="Force reboot in a hard or clean way. Default: clean")

    @staticmethod
    def mutate(root, info, ref, force: Optional[ShutdownForce] = ShutdownForce.CLEAN):
        if force == ShutdownForce.HARD:
            access_action = VM.Actions.hard_reboot
            method = 'async_hard_reboot'
        elif force == ShutdownForce.CLEAN:
            access_action = VM.Actions.clean_reboot
            method = 'async_clean_reboot'

        @with_authentication(access_class=VM, access_action=access_action)
        def get_vm(*args, **kwargs):
            return kwargs['VM']

        vm = get_vm(root, info, ref, force)
        if not vm:
            return VMRebootMutation(granted=False)

        call = getattr(vm, method)
        return VMRebootMutation(taskId=call(), granted=True)


class VMPauseMutation(graphene.Mutation):
    taskId = graphene.ID(required=False, description="Pause/unpause task ID")
    granted = graphene.Boolean(required=True, description="Shows if access to pause is granted")
    reason = graphene.String()

    class Arguments:
        ref = graphene.ID(required=True)

    @staticmethod
    @with_authentication
    def mutate(root, info, ref):
        ctx: ContextProtocol = info.context

        vm = VM(ctx.xen, ref)
        power_state = vm.get_power_state()
        if power_state == "Running":
            access_action = VM.Actions.pause
            method = 'async_pause'
        elif power_state == "Paused":
            access_action = VM.Actions.unpause
            method = 'async_unpause'
        else:
            return VMPauseMutation(granted=False, reason=f"Power state is {power_state}, expected: Running or Paused")


        if not vm.check_access(ctx.user_authenticator, access_action):
            return VMPauseMutation(granted=False, reason=f"Access to action {access_action} for VM {vm.ref} is not granted")

        return VMPauseMutation(taskId=getattr(vm, method)(), granted=True)


class VMDeleteMutation(graphene.Mutation):
    taskId = graphene.ID(required=False, description="Deleting task ID")
    granted = graphene.Boolean(required=True, description="Shows if access to delete is granted")
    reason = graphene.String()

    class Arguments:
        ref = graphene.ID(required=True)

    @staticmethod
    @with_authentication(access_class=VM, access_action=VM.Actions.destroy)
    @return_if_access_is_not_granted([("VM", "ref", VM.Actions.destroy)])
    def mutate(root, info, ref, VM):
        if VM.get_power_state() == "Halted":
            return VMDeleteMutation(taskId=VM.async_destroy(), granted=True)
        else:
            return VMDeleteMutation(granted=False, reason=f"Power state of VM {VM.ref} is not Halted, unable to delete")


