import graphene

from handlers.graphql.resolvers.network import networkType, resolve_network
from handlers.graphql.resolvers.vm import vmType, resolve_vm
from handlers.graphql.types.gxenobjecttype import GXenObjectType
from xenadapter.xenobject import XenObject, GXenObject


class GVIF(GXenObjectType):
    ref = graphene.Field(graphene.ID, required=True,
                         description="Unique constant identifier/object reference (primary)")
    MAC = graphene.Field(graphene.ID, required=True, description="MAC address")
    VM = graphene.Field(vmType, resolver=resolve_vm)
    device = graphene.Field(graphene.ID, required=True, description="Device ID")
    currently_attached = graphene.Field(graphene.Boolean, required=True)
    ip = graphene.Field(graphene.String)
    ipv4 = graphene.Field(graphene.String)
    ipv6 = graphene.Field(graphene.String)
    network = graphene.Field(networkType, resolver=resolve_network)

class VIF(XenObject):
    api_class = 'VIF'
    EVENT_CLASSES = ['vif']
    db_table_name = 'vifs'
    GraphQLType = GVIF

