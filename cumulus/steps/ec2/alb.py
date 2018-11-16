from cumulus.chain import step
from troposphere import (
    Ref, Not, Equals, Join, ec2,
    If, Output
)
from troposphere import elasticloadbalancingv2 as alb

SG_NAME = "%sSecurityGroup"
ALB_LISTENER = "%sListener"
ALB_NAME = "LoadBalancer"
TARGET_GROUP_DEFAULT = "TargetGroup"


class Alb(step.Step):

    def __init__(self,
                 prefix,
                 ):
        """

        :type prefix: basestring prefix to name components uniquely
        """
        step.Step.__init__(self, name='Alb')
        self.prefix = prefix

    def handle(self, chain_context):
        sg_name = self.prefix + SG_NAME % self.name

        self.create_conditions(chain_context.template)
        self.create_security_groups(chain_context.template, sg_name)
        self.create_default_target_group(chain_context.template)
        self.create_load_balancer_alb(chain_context.template, sg_name)
        self.add_listener(chain_context.template)

    def create_conditions(self, template):
        template.add_condition(
            "UseSSL",
            Not(Equals(Ref("ALBCertName"), ""))
        )
        template.add_condition(
            "UseIAMCert",
            Not(Equals(Ref("ALBCertType"), "acm")))

    def create_security_groups(self, template, sg_name):

        template.add_resource(
            ec2.SecurityGroup(
                sg_name,
                GroupName=sg_name,
                GroupDescription=sg_name,
                VpcId=Ref("VpcId"),
                Tags=[{'Key': 'Name', 'Value': sg_name}]
            ))

        template.add_output(
            Output("InternalAlbSG", Value=Ref(sg_name))
        )

        sg_ingress_name = "SecurityGroupIngressTo443"

        # TODO: take a list of Cidr's
        # Allow Internet to connect to ALB
        template.add_resource(ec2.SecurityGroupIngress(
            sg_ingress_name,
            IpProtocol="tcp", FromPort="443", ToPort="443",
            CidrIp="10.0.0.0/0",
            GroupId=Ref(sg_name),
        ))

    def create_load_balancer_alb(self, template, sg_name):
        alb_name = ALB_NAME

        load_balancer = template.add_resource(alb.LoadBalancer(
            alb_name,
            Scheme="internal",
            Subnets=Ref("PrivateSubnets"),
            SecurityGroups=[Ref(sg_name)]
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

    def add_listener(self, template):
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
        alb_name = ALB_NAME
        with_ssl = alb.Listener(
            ALB_LISTENER % self.name,
            Port="443",
            Protocol="HTTPS",
            LoadBalancerArn=Ref(alb_name),
            DefaultActions=[alb.Action(
                Type="forward",
                TargetGroupArn=Ref(TARGET_GROUP_DEFAULT)
            )],
            Certificates=[alb.Certificate(
                CertificateArn=cert_id
            )]
        )

        template.add_resource(with_ssl)

        template.add_output(
            Output("IAlbListener", Value=with_ssl.Ref())
        )

    def create_default_target_group(self, template):
        """

        :param template:
        :param instance_name:
        """
        template.add_resource(alb.TargetGroup(
            TARGET_GROUP_DEFAULT,
            Port='80',
            Protocol="HTTP",
            VpcId=Ref("VpcId"),
        ))
