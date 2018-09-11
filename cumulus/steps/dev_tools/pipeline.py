import awacs
import troposphere

import awacs.iam
import awacs.aws
import awacs.sts
import awacs.s3
import awacs.logs
import awacs.ec2
import awacs.iam
import awacs.codecommit

from cumulus.chain import step
import cumulus.steps.dev_tools

from troposphere import codepipeline, Ref, iam
from troposphere.s3 import Bucket, VersioningConfiguration

# SOURCE_STAGE_OUTPUT_NAME = 'SourceStageOutput'


class Pipeline(step.Step):

    def __init__(self, name, bucket_name):
        """

        :type bucket_name: the name of the bucket that will be created suffixed with the chaincontext instance name
        """
        step.Step.__init__(self)
        self.name = name
        self.bucket_name = bucket_name

    def handle(self, chain_context):
        """
        This step adds in the shell of a pipeline.
         * s3 bucket
         * policies for the bucket and pipeline
         * your next step in the chain MUST be a source stage
        :param chain_context:
        :return:
        """
        # TODO: let (force?) bucket to be injected.
        pipeline_bucket = Bucket(
            "pipelinebucket%s" % chain_context.instance_name,
            BucketName=self.bucket_name,
            VersioningConfiguration=VersioningConfiguration(
                Status="Enabled"
            )
        )

        pipeline_bucket_access_policy = iam.ManagedPolicy(
            "PipelineBucketAccessPolicy",
            Path='/managed/',
            PolicyDocument=awacs.aws.PolicyDocument(
                Version="2012-10-17",
                Id="bucket-access-policy%s" % chain_context.instance_name,
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[
                            awacs.s3.ListBucket,
                            awacs.s3.GetBucketVersioning,
                        ],
                        Resource=[
                            troposphere.Join('', [
                                awacs.s3.ARN(),
                                Ref(pipeline_bucket),
                            ]),
                        ],
                    ),
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[
                            awacs.s3.HeadBucket,
                        ],
                        Resource=[
                            '*'
                        ]
                    ),
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[
                            awacs.s3.GetObject,
                            awacs.s3.GetObjectVersion,
                            awacs.s3.PutObject,
                            awacs.s3.ListObjects,
                            awacs.s3.ListBucketMultipartUploads,
                            awacs.s3.AbortMultipartUpload,
                            awacs.s3.ListMultipartUploadParts,
                            awacs.aws.Action("s3", "Get*"),
                        ],
                        Resource=[
                            troposphere.Join('', [
                                awacs.s3.ARN(),
                                Ref(pipeline_bucket),
                                '/*'
                            ]),
                        ],
                    )
                ]
            )
        )

        chain_context.template.add_resource(pipeline_bucket_access_policy)
        # pipeline_bucket could be a string or Join object.. unit test this.
        chain_context.metadata[cumulus.steps.dev_tools.META_PIPELINE_BUCKET_REF] = Ref(pipeline_bucket)
        chain_context.metadata[cumulus.steps.dev_tools.META_PIPELINE_BUCKET_POLICY_REF] = Ref(pipeline_bucket_access_policy)

        pipeline_policy = iam.Policy(
            PolicyName="%sPolicy" % self.name,
            PolicyDocument=awacs.aws.PolicyDocument(
                Version="2012-10-17",
                Id="PipelinePolicy",
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        # TODO: actions here could be limited more
                        Action=[awacs.aws.Action("s3", "*")],
                        Resource=[
                            troposphere.Join('', [
                                awacs.s3.ARN(),
                                Ref(pipeline_bucket),
                                "/*"
                            ]),
                        ],
                    ),
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[awacs.aws.Action("s3", "*")],
                        Resource=[
                            troposphere.Join('', [
                                awacs.s3.ARN(),
                                Ref(pipeline_bucket),
                            ]),
                        ],
                    ),
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[
                            awacs.aws.Action("cloudformation", "*"),
                            awacs.aws.Action("codebuild", "*"),
                        ],
                        # TODO: restrict more accurately
                        Resource=["*"]
                    ),
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[
                            awacs.codecommit.GetBranch,
                            awacs.codecommit.GetCommit,
                            awacs.codecommit.UploadArchive,
                            awacs.codecommit.GetUploadArchiveStatus,
                            awacs.codecommit.CancelUploadArchive
                        ],
                        Resource=["*"]
                    ),
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[
                            awacs.iam.PassRole
                        ],
                        Resource=["*"]
                    ),
                ],
            )
        )

        pipeline_service_role = iam.Role(
            "PipelineServiceRole",
            Path="/",
            RoleName="PipelineRole%s" % chain_context.instance_name,
            AssumeRolePolicyDocument=awacs.aws.Policy(
                Statement=[
                    awacs.aws.Statement(
                        Effect=awacs.aws.Allow,
                        Action=[awacs.sts.AssumeRole],
                        Principal=awacs.aws.Principal(
                            'Service',
                            "codepipeline.amazonaws.com"
                        )
                    )]
            ),
            Policies=[
                pipeline_policy
            ]
        )

        generic_pipeline = codepipeline.Pipeline(
            "Pipeline",
            # Name=chain_context.instance_name,
            RoleArn=troposphere.GetAtt(pipeline_service_role, "Arn"),
            Stages=[],
            ArtifactStore=codepipeline.ArtifactStore(
                Type="S3",
                Location=Ref(pipeline_bucket)
            )
        )

        pipeline_output = troposphere.Output(
            "PipelineLogicalName",
            Description="Pipeline (logical id)",
            Value=Ref(generic_pipeline),
        )

        chain_context.template.add_resource(pipeline_bucket)
        chain_context.template.add_resource(pipeline_service_role)
        chain_context.template.add_resource(generic_pipeline)
        chain_context.template.add_output(pipeline_output)
