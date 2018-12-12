import awacs
import awacs.aws
import awacs.sts
from troposphere import iam, codepipeline, GetAtt

import cumulus.policies
import cumulus.policies.cloudformation
import cumulus.types.codebuild.buildaction
import cumulus.util.template_query
from cumulus.chain import step
from cumulus.steps.dev_tools import META_PIPELINE_BUCKET_POLICY_REF


class CloudFormationAction(step.Step):
    OUTPUT_FILE_NAME = 'StackOutputs.json'

    def __init__(self,
                 action_name,
                 input_artifact_names,
                 input_template_path,
                 input_template_configuration,
                 stage_name_to_add,
                 stack_name,
                 action_mode,
                 output_artifact_name=None,
                 cfn_action_role_arn=None,
                 cfn_action_config_role_arn=None,
                 cfn_param_overrides=None,
                 ):
        """
        :type cfn_action_config_role_arn: [troposphere.iam.Policy]
        :type action_name: basestring Displayed on the console
        :type input_artifact_names: [basestring] List of input artifacts
        :type input_template_path: basestring Full path to cloudformation template (ex. ArtifactName::templatefolder/template.json)
        :type input_configuration: basestring Full path to cloudformation config file (ex. ArtifactName::envfolder/parameters.json)
        :type stage_name_to_add: basestring Name of the pipeline stage to add this action to
        :type stack_name: basestring name of the stack that this action will build
        :type action_mode: cumulus.types.cloudformation.action_mode.ActionMode The actual CloudFormation action to execute
        """
        step.Step.__init__(self)
        self.cfn_param_overrides = cfn_param_overrides
        self.action_name = action_name
        self.input_artifact_names = input_artifact_names
        self.input_template_path = input_template_path
        self.input_template_configuration = input_template_configuration
        self.stage_name_to_add = stage_name_to_add
        self.stack_name = stack_name
        self.action_mode = action_mode
        self.output_artifact_name = output_artifact_name
        self.cfn_action_role_arn = cfn_action_role_arn
        self.cfn_action_config_role_arn = cfn_action_config_role_arn

    def handle(self, chain_context):

        print("Adding action %sstage" % self.action_name)
        # if supplied, use the role injected in, otherwise, build one.
        if self.cfn_action_config_role_arn:
            cfn_configuration_role_arn = self.cfn_action_config_role_arn
        else:
            cfn_configuration_role = self.get_cfn_role(
                chain_context=chain_context,
            )
            cfn_configuration_role_arn = GetAtt(cfn_configuration_role, 'Arn')
            chain_context.template.add_resource(cfn_configuration_role)

        input_artifacts = []
        for artifact_name in self.input_artifact_names:
            input_artifacts.append(codepipeline.InputArtifacts(
                Name=artifact_name
            ))

        cloud_formation_action = cumulus.types.codebuild.buildaction.CloudFormationAction(
            Name=self.action_name,
            InputArtifacts=input_artifacts,
            Configuration={
                'ActionMode': self.action_mode.value,
                # this role needs to be the cfn role above, and it should add the tools account policy
                'RoleArn': cfn_configuration_role_arn,
                'StackName': self.stack_name,
                'Capabilities': 'CAPABILITY_NAMED_IAM',
                'TemplateConfiguration': self.input_template_configuration,
                'TemplatePath': self.input_template_path,
            },
            RunOrder="1"
        )

        # Add optional configuration
        if self.output_artifact_name:
            output_artifact = codepipeline.OutputArtifacts(
                Name=self.output_artifact_name
            )
            cloud_formation_action.OutputArtifacts = [
                output_artifact
            ]
            cloud_formation_action.Configuration['OutputFileName'] = CloudFormationAction.OUTPUT_FILE_NAME

        if self.cfn_action_role_arn:
            cloud_formation_action.RoleArn = self.cfn_action_role_arn

        if self.cfn_param_overrides:
            cloud_formation_action.Configuration['ParameterOverrides'] = self.cfn_param_overrides

        stage = cumulus.util.template_query.TemplateQuery.get_pipeline_stage_by_name(
            template=chain_context.template,
            stage_name=self.stage_name_to_add,
        )

        # TODO accept a parallel action to the previous action, and don't +1 here.
        next_run_order = len(stage.Actions) + 1
        cloud_formation_action.RunOrder = next_run_order
        stage.Actions.append(cloud_formation_action)

    def get_cfn_role(self, chain_context, step_policies=None):
        """
        Default role for cloudformation with access to the S3 bucket and cloudformation assumerole.
        :param chain_context: chaincontext.ChainContext
        :type step_policies: [troposphere.iam.Policy]
        """
        policy_name = "CloudFormationPolicy%sStage" % chain_context.instance_name
        role_name = "CloudFormationRole%sStage" % self.action_name

        all_policies = [
            cumulus.policies.cloudformation.get_policy_cloudformation_general_access(policy_name)
        ]

        if step_policies:
            all_policies += step_policies

        cloud_formation_role = iam.Role(
            role_name,
            Path="/",
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[awacs.sts.AssumeRole],
                        Principal=awacs.aws.Principal(
                            'Service',
                            ["cloudformation.amazonaws.com"]
                        )
                    )]
            ),
            Policies=all_policies,
            ManagedPolicyArns=[
                chain_context.metadata[META_PIPELINE_BUCKET_POLICY_REF]
            ]
        )
        return cloud_formation_role
