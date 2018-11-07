from troposphere import (
    Ref, Join)
from troposphere import route53

from cumulus.chain import step


class Dns(step.Step):

    def __init__(self,
                 namespace,
                 base_domain,
                 hosted_zone_id,
                 dns_name,
                 ):

        step.Step.__init__(self)

        self.base_domain = base_domain
        self.namespace = namespace
        self.hosted_zone_id = hosted_zone_id
        self.dns_name = dns_name

    def handle(self, chain_context):
        template = chain_context.template

        name = 'AlbAlias%s' % chain_context.instance_name

        template.add_resource(route53.RecordSetGroup(
            "Route53Records",
            RecordSets=[
                route53.RecordSet(
                    name,
                    Weight=1,
                    SetIdentifier="original",
                    AliasTarget=route53.AliasTarget(
                        HostedZoneId=self.hosted_zone_id,
                        DNSName=self.dns_name,
                        EvaluateTargetHealth=False,
                    ),
                    Name=Join("", [
                        self.namespace,
                        "-",
                        Ref("env"),
                        ".",
                        self.base_domain,
                        "."
                    ]),
                    Type="A",
                )
            ],
            HostedZoneName=Join("", [self.base_domain, "."])
        ))
