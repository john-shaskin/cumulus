import awacs
from awacs import s3
from awacs.aws import Policy, Statement, Allow, Principal
from awacs.sts import AssumeRole
from troposphere import autoscaling, Ref, FindInMap, Base64, ec2, iam
from troposphere.iam import InstanceProfile, Role

from cumulus.chain import step
from cumulus.components.userdata.linux import LinuxUserData
from cumulus.steps.ec2 import META_SECURITY_GROUP_REF

SG_NAME = "%sSecurityGroup"
ASG_NAME = "AutoScalingGroup"
EC2_ROLE_NAME = "Ec2RoleName"
INSTANCE_PROFILE_NAME = "InstanceProfile"


class LaunchConfig(step.Step):

    def __init__(self,
                 prefix,
                 meta_data,
                 bucket_name,
                 vpc_id=None,
                 user_data=None):
        """

        :type user_data: basestring custom user data
        :type vpc_id: object
        :type bucket_name: basestring custom bucket name
        :type meta_data: basestring custom metadata
        :type prefix: basestring the prefix you want to name various components with
        """
        step.Step.__init__(self,
                           name='LaunchConfig')
        self.prefix = prefix
        self.user_data = user_data
        self.meta_data = meta_data
        self.bucket_name = bucket_name
        self.vpc_id = vpc_id

    def handle(self, chain_context):
        template = chain_context.template

        sg_name = self.prefix + SG_NAME % self.name

        launch_config_security_group = ec2.SecurityGroup(
            sg_name,
            GroupName=sg_name,
            GroupDescription=sg_name,
            **self._get_security_group_parameters(sg_name)
        )

        chain_context.metadata[META_SECURITY_GROUP_REF] = Ref(sg_name)

        instance_profile = self._get_instance_profile(chain_context)

        # We will assume the default case is linux user data
        if self.user_data is None:
            self.user_data = LinuxUserData(launch_config_name=self.name,
                                           asg_name=ASG_NAME,
                                           config_sets='default')

        launch_config = autoscaling.LaunchConfiguration(
            self.name,
            UserData=Base64(self.user_data.user_data_for_cfn_init()),
            Metadata=self.meta_data,
            IamInstanceProfile=Ref(instance_profile),
            **self._get_launch_configuration_parameters(chain_context)
        )

        template.add_resource(instance_profile)
        template.add_resource(launch_config_security_group)
        template.add_resource(launch_config)

    def _get_security_group_parameters(self, sg_name):
        config = {}

        if self.vpc_id:
            config['VpcId'] = self.vpc_id

        config['Tags'] = [{'Key': 'Name', 'Value': sg_name}]

        return config

    def _get_launch_configuration_parameters(self, chain_context):
        asg_sg_list = [chain_context.metadata[META_SECURITY_GROUP_REF]]

        parameters = {
            'ImageId': FindInMap('AmiMap',
                                 Ref("AWS::Region"),
                                 Ref('ImageName')),
            'InstanceType': Ref("InstanceType"),
            'KeyName': Ref("SshKeyName"),
            'SecurityGroups': asg_sg_list,
        }

        return parameters

    def _get_instance_profile(self, chain_context):
        s3readPolicy = iam.Policy(
            PolicyName='S3ReadArtifactBucket',
            PolicyDocument=Policy(
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[
                            awacs.s3.GetObject,
                        ],
                        Resource=[s3.ARN(self.bucket_name + "/*")]
                    ),
                    Statement(
                        Effect=Allow,
                        Action=[
                            awacs.s3.ListBucket,
                        ],
                        Resource=[s3.ARN(self.bucket_name)]
                    )
                ]
            )
        )

        cfnrole = chain_context.template.add_resource(Role(
            EC2_ROLE_NAME,
            AssumeRolePolicyDocument=Policy(
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[AssumeRole],
                        Principal=Principal("Service", ["ec2.amazonaws.com"])
                    )
                ]
            ),
            Policies=[s3readPolicy]
        ))

        instance_profile = InstanceProfile(
            INSTANCE_PROFILE_NAME,
            Roles=[Ref(cfnrole)]
        )
        return instance_profile
