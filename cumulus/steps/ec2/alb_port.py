from troposphere import (
    Ref, ec2)

from cumulus.chain import step
from cumulus.steps.ec2 import META_SECURITY_GROUP_REF

ALB_PORT_NAME = "AlbPortToOpen%s"


class AlbPort(step.Step):

    def __init__(self,
                 port_to_open):
        step.Step.__init__(self, name='')

        self.port_to_open = port_to_open

    def handle(self, chain_context):
        template = chain_context.template

        template.add_resource(ec2.SecurityGroupIngress(
            ALB_PORT_NAME % self.port_to_open,
            IpProtocol="tcp",
            FromPort=self.port_to_open,
            ToPort=self.port_to_open,
            SourceSecurityGroupId=Ref("AlbSg"),
            GroupId=chain_context.metadata[META_SECURITY_GROUP_REF]
        ))
