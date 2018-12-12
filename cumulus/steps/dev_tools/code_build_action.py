import awacs
import awacs.aws
import awacs.ec2
import awacs.iam
import awacs.logs
import awacs.s3
import awacs.sts
import troposphere
from troposphere import iam, \
    codebuild, codepipeline, Ref, Sub, ec2

import cumulus.policies
import cumulus.policies.codebuild
import cumulus.types.codebuild.buildaction
import cumulus.util.template_query
from cumulus.chain import step
from cumulus.steps.dev_tools import META_PIPELINE_BUCKET_POLICY_REF, \
    META_PIPELINE_BUCKET_NAME


class CodeBuildAction(step.Step):

    def __init__(self,
                 prefix,
                 stack_namespace,
                 action_name,
                 stage_name_to_add,
                 input_artifact_name,
                 environment=None,
                 vpc_config=None,
                 buildspec='buildspec.yml',
                 role_arn=None,
                 ):
        """
        :type prefix: basestring name to make the project unique
        :type buildspec: basestring path to buildspec.yml or text containing the buildspec.
        :type input_artifact_name: basestring The artifact name in the pipeline. Must contain a buildspec.yml
        :type action_name: basestring Displayed on the console
        :type environment: troposphere.codebuild.Environment Optional if you need ENV vars or a different build.
        :type vpc_config.Vpc_Config: Only required if the codebuild step requires access to the VPC
        :type stack_namespace: Stack namespace to generate a unique physical name to give the code build project
        """
        step.Step.__init__(self)
        self.prefix = prefix
        self.role_arn = role_arn
        self.buildspec = buildspec
        self.environment = environment
        self.input_artifact_name = input_artifact_name
        self.action_name = action_name
        self.vpc_config = vpc_config
        self.stage_name_to_add = stage_name_to_add
        self.stack_namespace = stack_namespace

    def handle(self, chain_context):

        self.validate(chain_context)

        print("Adding action %s Stage." % self.action_name)
        full_action_name = "%s%s" % (self.stage_name_to_add, self.action_name)

        policy_name = "%sCodeBuildPolicy" % chain_context.instance_name
        role_name = "CodeBuildRole%s" % full_action_name

        codebuild_role = self.get_default_code_build_role(
            chain_context=chain_context,
            policy_name=policy_name,
            role_name=role_name,
        )

        codebuild_role_arn = self.role_arn if self.role_arn else troposphere.GetAtt(codebuild_role, 'Arn')

        if not self.environment:
            self.environment = codebuild.Environment(
                ComputeType='BUILD_GENERAL1_SMALL',
                Image='aws/codebuild/python:2.7.12',
                Type='LINUX_CONTAINER',
                EnvironmentVariables=[
                    # TODO: allow these to be injectable, or just the whole environment?
                    {'Name': 'PIPELINE_BUCKET', 'Value': chain_context.metadata[META_PIPELINE_BUCKET_NAME]}
                ],
            )

        project = self.create_project(
            prefix=self.prefix,
            chain_context=chain_context,
            codebuild_role_arn=codebuild_role_arn,
            codebuild_environment=self.environment,
            name=full_action_name,
        )

        code_build_action = cumulus.types.codebuild.buildaction.CodeBuildAction(
            Name=self.action_name,
            InputArtifacts=[
                codepipeline.InputArtifacts(Name=self.input_artifact_name)
            ],
            Configuration={'ProjectName': Ref(project)},
            RunOrder="1"
        )

        chain_context.template.add_resource(codebuild_role)
        chain_context.template.add_resource(project)

        template = chain_context.template
        stage = cumulus.util.template_query.TemplateQuery.get_pipeline_stage_by_name(
            template=template,
            stage_name=self.stage_name_to_add,
        )

        # TODO accept a parallel action to the previous action, and don't +1 here.
        next_run_order = len(stage.Actions) + 1
        code_build_action.RunOrder = next_run_order
        stage.Actions.append(code_build_action)

    def get_default_code_build_role(self, chain_context, policy_name, role_name):
        codebuild_role = iam.Role(
            role_name,
            Path="/",
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[awacs.sts.AssumeRole],
                        Principal=awacs.aws.Principal(
                            'Service',
                            "codebuild.amazonaws.com"
                        )
                    )]
            ),
            Policies=[
                cumulus.policies.codebuild.get_policy_code_build_general_access(policy_name)
            ],
            ManagedPolicyArns=[
                chain_context.metadata[META_PIPELINE_BUCKET_POLICY_REF]
            ]
        )
        return codebuild_role

    def create_project(self, chain_context, codebuild_role_arn, codebuild_environment, name, prefix):

        artifacts = codebuild.Artifacts(Type='CODEPIPELINE')

        vpc_config = {}

        # Configure vpc if available
        if self.vpc_config:
            sg = ec2.SecurityGroup(
                "CodebBuild%s%sSG" % (self.stage_name_to_add, self.action_name),
                GroupDescription="Gives codebuild access to VPC",
                VpcId=self.vpc_config.vpc_id,
                SecurityGroupEgress=[
                    {
                        "IpProtocol": "-1",
                        "CidrIp": "0.0.0.0/0",
                        "FromPort": "0",
                        "ToPort": "65535",
                    }
                ],
            )
            chain_context.template.add_resource(sg)
            vpc_config = {'VpcConfig': codebuild.VpcConfig(
                VpcId=self.vpc_config.vpc_id,
                Subnets=self.vpc_config.subnets,
                SecurityGroupIds=[Ref(sg)],
            )}

        project_name = "%sProject%s" % (prefix, name)

        print("Action %s is using buildspec: " % self.action_name)
        print(self.buildspec)

        project = codebuild.Project(
            project_name,
            Artifacts=artifacts,
            Environment=codebuild_environment,
            Name=Sub(['${StackNamespace}-${ProjectName}', {
                'StackNamespace': self.stack_namespace,
                'ProjectName': project_name
            }]),
            ServiceRole=codebuild_role_arn,
            Source=codebuild.Source(
                "Deploy",
                Type='CODEPIPELINE',
                BuildSpec=self.buildspec,
            ),
            **vpc_config
        )

        return project

    def validate(self, chain_context):
        if META_PIPELINE_BUCKET_POLICY_REF not in chain_context.metadata:
            raise AssertionError("Could not find expected 'META_PIPELINE_BUCKET_POLICY_REF' in metadata. "
                                 "Maybe you added the code build step to the chain before the pipeline step?")
