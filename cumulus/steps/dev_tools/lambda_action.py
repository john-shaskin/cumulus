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


class LambdaAction(step.Step):

    def __init__(self,
                 action_name,
                 input_artifact_name,
                 stage_name_to_add,
                 function_name,
                 user_parameters=None,
                 ):
        """
        :type buildspec: basestring path to buildspec.yml or text containing the buildspec.
        :type input_artifact_name: basestring The artifact name in the pipeline. Must contain a buildspec.yml
        :type action_name: basestring Displayed on the console
        :type environment: troposphere.codebuild.Environment Optional if you need ENV vars or a different build.
        :type vpc_config.Vpc_Config: Only required if the codebuild step requires access to the VPC
        """
        step.Step.__init__(self)
        self.user_parameters = user_parameters
        self.function_name = function_name
        self.input_artifact_name = input_artifact_name
        self.action_name = action_name
        self.stage_name_to_add = stage_name_to_add

    def handle(self, chain_context):

        print("Adding action %s to Stage." % self.action_name)
        suffix = "%s%s" %(self.stage_name_to_add, self.action_name)

        policy_name = "LambdaPolicy%s" % chain_context.instance_name
        role_name = "LambdaRole%s" % suffix

        lambda_role = iam.Role(
            role_name,
            Path="/",
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[awacs.sts.AssumeRole],
                        Principal=awacs.aws.Principal(
                            'Service',
                            "lambda.amazonaws.com"
                        )
                    )]
            ),
            Policies=[
                # TODO: new policy
                cumulus.policies.codebuild.get_policy_code_build_general_access(policy_name)
            ],
            ManagedPolicyArns=[
                chain_context.metadata[META_PIPELINE_BUCKET_POLICY_REF]
            ]
        )


        lambda_action = cumulus.types.codebuild.buildaction.LambdaAction(
            Name=self.action_name,
            InputArtifacts=[
                codepipeline.InputArtifacts(Name=self.input_artifact_name)
            ],
            Configuration={
                'FunctionName': self.function_name
            },
            RunOrder="1"
        )

        chain_context.template.add_resource(lambda_role)

        stage = cumulus.util.tropo.TemplateQuery.get_pipeline_stage_by_name(
            template=chain_context.template,
            stage_name=self.stage_name_to_add,
        )

        # TODO accept a parallel action to the previous action, and don't +1 here.
        next_run_order = len(stage.Actions) + 1
        lambda_action.RunOrder = next_run_order
        stage.Actions.append(lambda_action)
