import troposphere.codepipeline


class SourceS3Action(troposphere.codepipeline.Actions):
    """
        This class doesn't do much except set the ActionType to reduce code clutter
    """
    def __init__(self, **kwargs):
        super(SourceS3Action, self).__init__(**kwargs)

        self.ActionTypeId = troposphere.codepipeline.ActionTypeId(
                Category="Source",
                Owner="AWS",
                Version="1",
                Provider='S3',
            )
        self.RunOrder = "1"


class SourceCodeCommitAction(troposphere.codepipeline.Actions):
    """
        This class doesn't do much except set the ActionType to reduce code clutter
    """
    def __init__(self, **kwargs):
        super(SourceCodeCommitAction, self).__init__(**kwargs)

        self.ActionTypeId = troposphere.codepipeline.ActionTypeId(
                Category="Source",
                Owner="AWS",
                Version="1",
                Provider="CodeCommit",
            )
        self.RunOrder = "1"


class CodeBuildAction(troposphere.codepipeline.Actions):
    """
        This class doesn't do much except set the ActionType to reduce code clutter
    """
    def __init__(self, **kwargs):
        super(CodeBuildAction, self).__init__(**kwargs)

        self.ActionTypeId = troposphere.codepipeline.ActionTypeId(
                Category="Build",
                Owner="AWS",
                Version="1",
                Provider="CodeBuild"
            )
        self.RunOrder = "1"


class ApprovalAction(troposphere.codepipeline.Actions):
    """
      This class doesn't do much except set the ActionType to reduce code clutter
    """
    def __init__(self, **kwargs):
        super(ApprovalAction, self).__init__(**kwargs)

        self.ActionTypeId = troposphere.codepipeline.ActionTypeId(
            Category="Approval",
            Owner="AWS",
            Version="1",
            Provider="Manual"
        )
        self.RunOrder = "1"


class CloudFormationAction(troposphere.codepipeline.Actions):
    """
      This class doesn't do much except set the ActionType to reduce code clutter
    """
    def __init__(self, **kwargs):
        super(CloudFormationAction, self).__init__(**kwargs)

        self.ActionTypeId = troposphere.codepipeline.ActionTypeId(
            Category="Deploy",
            Owner="AWS",
            Version="1",
            Provider="CloudFormation"
        )
        self.RunOrder = "1"
