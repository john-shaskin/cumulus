from troposphere import Join
from troposphere import route53

from cumulus.chain import step

DNS_NAME = 'AlbAlias%s'


class Dns(step.Step):

    def __init__(self,
                 dns_name,
                 base_domain,
                 hosted_zone_id,
                 target,
                 ):
        step.Step.__init__(self, name='Dns')

        self.target = target
        self.base_domain = base_domain
        self.hosted_zone_id = hosted_zone_id
        self.dns_name = dns_name

    def handle(self, chain_context):
        template = chain_context.template

        template.add_resource(route53.RecordSetGroup(
            "Route53Records",
            RecordSets=[
                route53.RecordSet(
                    DNS_NAME % self.name,
                    Weight=1,
                    SetIdentifier="original",
                    AliasTarget=route53.AliasTarget(
                        HostedZoneId=self.hosted_zone_id,
                        DNSName=self.target,
                        EvaluateTargetHealth=False,
                    ),
                    Name=Join("", [
                        self.dns_name,
                        ".",
                        self.base_domain,
                        "."
                    ]),
                    Type="A",
                )
            ],
            HostedZoneName=Join("", [self.base_domain, "."])
        ))
