import awacs
import troposphere

import awacs.aws
import awacs.logs
import awacs.s3
import awacs.iam
import awacs.ec2
import awacs.sts

import cumulus.policies
import cumulus.policies.codebuild
import cumulus.types.codebuild.buildaction
import cumulus.util.tropo

from troposphere import iam,\
    codebuild, codepipeline, Ref, ec2

from cumulus.chain import step

from cumulus.steps.dev_tools import META_PIPELINE_BUCKET_POLICY_REF, \
    META_PIPELINE_BUCKET_REF


class CodeBuildAction(step.Step):

    def __init__(self,
                 action_name,
                 input_artifact_name,
                 stage_name_to_add,
                 environment=None,
                 vpc_config=None,
                 buildspec='buildspec.yml'):
        """
        :type buildspec: basestring path to buildspec.yml or text containing the buildspec.
        :type input_artifact_name: basestring The artifact name in the pipeline. Must contain a buildspec.yml
        :type action_name: basestring Displayed on the console
        :type environment: troposphere.codebuild.Environment Optional if you need ENV vars or a different build.
        :type vpc_config.Vpc_Config: Only required if the codebuild step requires access to the VPC
        """
        step.Step.__init__(self)
        self.buildspec = buildspec
        self.environment = environment
        self.input_artifact_name = input_artifact_name
        self.action_name = action_name
        self.vpc_config = vpc_config
        self.stage_name_to_add = stage_name_to_add

    def handle(self, chain_context):

        print("Adding action %s Stage." % self.action_name)
        suffix = "%s%s" %(self.stage_name_to_add, self.action_name)

        policy_name = "CodeBuildPolicy%s" % chain_context.instance_name
        role_name = "CodeBuildRole%s" % suffix

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

        if not self.environment:
            self.environment = codebuild.Environment(
                ComputeType='BUILD_GENERAL1_SMALL',
                Image='aws/codebuild/python:2.7.12',
                Type='LINUX_CONTAINER',
                EnvironmentVariables=[
                    # TODO: allow these to be injectable, or just the whole environment?
                    {'Name': 'PIPELINE_BUCKET', 'Value': chain_context.metadata[META_PIPELINE_BUCKET_REF]}
                ],
            )

        project = self.create_project(
            chain_context=chain_context,
            codebuild_role=codebuild_role,
            codebuild_environment=self.environment,
            name=self.action_name + suffix,
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
        stage = cumulus.util.tropo.TemplateQuery.get_pipeline_stage_by_name(
            template=template,
            stage_name=self.stage_name_to_add,
        )

        # TODO accept a parallel action to the previous action, and don't +1 here.
        next_run_order = len(stage.Actions) + 1
        code_build_action.RunOrder = next_run_order
        stage.Actions.append(code_build_action)

    def create_project(self, chain_context, codebuild_role, codebuild_environment, name):

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

        project_name = "project%s" % name

        print("Action %s is using buildspec: " % self.action_name)
        print(self.buildspec)

        project = codebuild.Project(
            project_name,
            DependsOn=codebuild_role,
            Artifacts=artifacts,
            Environment=codebuild_environment,
            Name=project_name,
            ServiceRole=troposphere.GetAtt(codebuild_role, 'Arn'),
            Source=codebuild.Source(
                "Deploy",
                Type='CODEPIPELINE',
                BuildSpec=self.buildspec,
            ),
            **vpc_config
        )

        return project
