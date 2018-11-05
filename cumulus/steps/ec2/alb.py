from cumulus.chain import step
from troposphere import (
    Ref, Not, Equals, Join, ec2,
    If, Output
)
from troposphere import elasticloadbalancingv2 as alb

CLUSTER_SG_NAME = "%sSG"
ALB_NAME = "%sLoadBalancer"
TARGET_GROUP_DEFAULT = "%sTargetGroup"


class Alb(step.Step):

    def __init__(self,
                 alb_security_group_name,
                 alb_security_group_ingress_name,
                 ):
        self.alb_security_group_name = alb_security_group_name
        self.alb_security_group_ingress_name = alb_security_group_ingress_name
        step.Step.__init__(self)

    def handle(self, chain_context):
        self.create_conditions(chain_context.template)
        self.create_security_groups(chain_context.template, chain_context.instance_name)
        self.create_default_target_group(chain_context.template, chain_context.instance_name)
        self.create_load_balancer_alb(chain_context.template, chain_context.instance_name)
        self.add_listener(chain_context.template, chain_context.instance_name)

    def create_conditions(self, template):
        template.add_condition(
            "UseSSL",
            Not(Equals(Ref("ALBCertName"), ""))
        )
        template.add_condition(
            "UseIAMCert",
            Not(Equals(Ref("ALBCertType"), "acm")))

    def create_security_groups(self, template, instance_name):
        template.add_resource(
            ec2.SecurityGroup(
                self.alb_security_group_name,
                GroupDescription=self.alb_security_group_name,
                VpcId=Ref("VpcId")
            ))

        template.add_output(
            Output("InternalAlbSG", Value=Ref(self.alb_security_group_name))
        )

        # TODO: take a list of Cidr's
        # Allow Internet to connect to ALB
        template.add_resource(ec2.SecurityGroupIngress(
            self.alb_security_group_ingress_name,
            IpProtocol="tcp", FromPort="443", ToPort="443",
            CidrIp="10.0.0.0/0",
            GroupId=Ref(self.alb_security_group_name),
        ))

    def create_load_balancer_alb(self, template, instance_name):
        alb_name = ALB_NAME % instance_name

        load_balancer = template.add_resource(alb.LoadBalancer(
            alb_name,
            Scheme="internal",
            Subnets=Ref("PrivateSubnets"),
            SecurityGroups=[Ref(self.alb_security_group_name)]
        ))

        template.add_output(
            Output(
                "CanonicalHostedZoneID",
                Value=load_balancer.GetAtt("CanonicalHostedZoneID")
            )
        )
        template.add_output(
            Output("DNSName", Value=load_balancer.GetAtt("DNSName"))
        )

    def add_listener(self, template, instance_name):
        # Choose proper certificate source ?-> always acm?
        acm_cert = Join("", [
            "arn:aws:acm:",
            Ref("AWS::Region"),
            ":",
            Ref("AWS::AccountId"),
            ":certificate/", Ref("ALBCertName")])
        # We probably don't need this code for an IAM Cert
        iam_cert = Join("", [
            "arn:aws:iam::",
            Ref("AWS::AccountId"),
            ":server-certificate/",
            Ref("ALBCertName")])
        cert_id = If("UseIAMCert", iam_cert, acm_cert)
        alb_name = ALB_NAME % instance_name

        with_ssl = alb.Listener(
            "Listener",
            Port="443",
            Protocol="HTTPS",
            LoadBalancerArn=Ref(alb_name),
            DefaultActions=[alb.Action(
                Type="forward",
                TargetGroupArn=Ref(TARGET_GROUP_DEFAULT % instance_name)
            )],
            Certificates=[alb.Certificate(
                CertificateArn=cert_id
            )]
        )

        template.add_resource(with_ssl)

        template.add_output(
            Output("IAlbListener", Value=with_ssl.Ref())
        )

    def create_default_target_group(self, template, instance_name):
        """

        :param template:
        :param instance_name:
        """
        template.add_resource(alb.TargetGroup(
            TARGET_GROUP_DEFAULT % instance_name,
            Port='80',
            Protocol="HTTP",
            VpcId=Ref("VpcId"),
        ))
