from aind_behavior_dynamic_foraging.CurriculumManager.trainer import (
    DynamicForagingTrainerState,
    DynamicForagingTrainerServer
)
from aind_behavior_dynamic_foraging.CurriculumManager.trainer import DynamicForagingTrainerServer
from aind_behavior_dynamic_foraging.CurriculumManager.metrics import DynamicForagingMetrics
from aind_behavior_curriculum import Trainer
from aind_behavior_dynamic_foraging import AindDynamicForagingTaskLogic
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_dynamic_foraging.DataSchemas.optogenetics import Optogenetics
from aind_behavior_dynamic_foraging.DataSchemas.fiber_photometry import (
    FiberPhotometry,
    STAGE_STARTS
)
from aind_slims_api import SlimsClient
from aind_slims_api import models
from aind_data_schema.core.session import Session
import logging
import os
import math
from time import timezone
from datetime import datetime


class SlimsHandler:
    """
    Class to handle communication from slims to write waterlogs and curriculums
    """

    def __init__(self, task_logic: AindDynamicForagingTaskLogic,
                 session_model: AindBehaviorSessionModel,
                 opto_model: Optogenetics,
                 fip_model: FiberPhotometry,
                 username: str = None,
                 password: str = None):
        """
        :param task_logic: pydantic model that details the parameters used to run the behavior in a session
        :param session_model: pydantic model that details the parameters used to run session
        :param opto_model: pydantic model that details the parameters used to the optogenetics in a session
        :param fip_model: pydantic model that details the parameters used to the fip in a session
        :param username: Optional slims username. Will default to SLIMS_USERNAME environment variable if not provided
        :param password: Optional slims password. Will default to SLIMS_PASSWORD environment variable if not provided
        """

        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # set model attributes
        self.task_logic = task_logic
        self.session_model = session_model
        self.opto_model = opto_model
        self.fip_model = fip_model

        # connect to Slims
        self.slims_client = self.connect_to_slims(username, password)

        # set up Trainer and initialize curriculum and trainer
        self.trainer = DynamicForagingTrainerServer(slims_client=self.slims_client)
        self.curriculum = None
        self.trainer_state = None
        self.metrics = None
        self._loaded_mouse_id = None

    def connect_to_slims(self, username: str = None, password: str = None) -> SlimsClient:
        """
            Connect to Slims
        """

        try:
            self.log.info('Attempting to connect to Slims')
            slims_client = SlimsClient(username=username if username else os.environ['SLIMS_USERNAME'],
                                       password=password if password else os.environ['SLIMS_PASSWORD'])
        except KeyError as e:
            raise KeyError('SLIMS_USERNAME and SLIMS_PASSWORD do not exist as '
                           f'environment variables on machine. Please add. {e}')

        try:
            slims_client.fetch_model(models.SlimsMouseContent, barcode='00000000')
        except Exception as e:
            if 'Status 401 – Unauthorized' in str(e):  # catch error if username and password are incorrect
                raise Exception(f'Exception trying to read from Slims: {e}.\n'
                                f' Please check credentials:\n'
                                f'Username: {os.environ["SLIMS_USERNAME"]}\n'
                                f'Password: {os.environ["SLIMS_PASSWORD"]}')
            elif 'No record found' not in str(e):  # bypass if mouse doesn't exist
                raise Exception(f'Exception trying to read from Slims: {e}.\n')
        self.log.info('Successfully connected to Slims')

        return slims_client

    def add_waterlog_result(self, session: Session):
        """
            Add WaterLogResult to slims based on current state of gui
            :param session: Session object to pull water information from
        """

        try:  # try and find mouse
            self.log.info(f'Attempting to fetch mouse {session.subject_id} from Slims')
            mouse = self.slims_client.fetch_model(models.SlimsMouseContent, barcode=session.subject_id)
        except Exception as e:
            if 'No record found' in str(e):  # if no mouse found or validation errors on mouse
                self.log.warning(f'No record found" error while trying to fetch mouse {session.subject_id}. '
                                 f'Will not log water.')
                return
            else:
                self.log.error(f'While fetching mouse {session.subject_id} model, unexpected error occurred.')
                raise e

        # extract water information
        self.log.info('Extracting water information from first stimulus epoch')
        water_json = session.stimulus_epochs[0].output_parameters.water.items()
        water = {k: v if not (isinstance(v, float) and math.isnan(v)) else None for k, v in water_json}

        # extract software information
        self.log.info('Extracting software information from first data stream')
        software = session.stimulus_epochs[0].software[0]

        # create model
        self.log.info('Creating SlimsWaterlogResult based on session information.')
        model = models.SlimsWaterlogResult(
            mouse_pk=mouse.pk,
            date=session.session_start_time,
            weight_g=session.animal_weight_post,
            operator=self.session_model.experimenter[0],
            water_earned_ml=water['water_in_session_foraging'],
            water_supplement_delivered_ml=water['water_after_session'],
            water_supplement_recommended_ml=None,
            total_water_ml=water['water_in_session_total'],
            comments=session.notes,
            workstation=session.rig_id,
            sw_source=software.url,
            sw_version=software.version,
            test_pk=self.slims_client.fetch_pk("Test", test_name="test_waterlog"))

        # check if mouse already has waterlog for at session time and if, so update model
        self.log.info(f'Fetching previous waterlog for mouse {session.subject_id}')
        waterlog = self.slims_client.fetch_models(models.SlimsWaterlogResult, mouse_pk=mouse.pk, start=0, end=1)
        if waterlog != [] and waterlog[0].date.strftime("%Y-%m-%d %H:%M:%S") == \
                session.session_start_time.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"):
            self.log.info(f'Waterlog information already exists for this session. Updating waterlog in Slims.')
            model.pk = waterlog[0].pk
            self.slims_client.update_model(model=model)
        else:
            self.log.info(f'Adding waterlog to Slims.')
            self.slims_client.add_model(model)

    def get_added_mice(self) -> list[models.SlimsMouseContent]:
        """
            Return list of mice on slims
        """
        return self.slims_client.fetch_models(models.SlimsMouseContent)

    def load_mouse_curriculum(self, mouse_id: str) -> tuple[DynamicForagingTrainerState,
                                                            models.behavior_session.SlimsBehaviorSession]:
        """
            Load in specified mouse from slims
            :params mouse_id: mouse id string to load from slims
        """

        try:
            self.log.info(f"Fetching {mouse_id} from Slims.")
            self.slims_client.fetch_model(models.SlimsMouseContent, barcode=mouse_id)
            self.log.info(f"Successfully fetched {mouse_id} from Slims.")

            self.log.info(f"Fetching curriculum, trainer_state, and metrics for {mouse_id} from Slims.")
            self.curriculum, self.trainer_state, self.metrics, attachments, session = self.trainer.load_data(mouse_id)
            self.task_logic = AindDynamicForagingTaskLogic(**self.trainer_state.stage.task.model_dump())
            attachment_names = [attachment.name for attachment in attachments]

            # update session model with slims session information
            ses_att = attachments[attachment_names.index(AindBehaviorSessionModel.__name__)]
            slims_session_model = AindBehaviorSessionModel(**self.slims_client.fetch_attachment_content(ses_att).json())
            self.session_model.experiment = slims_session_model.experiment
            self.session_model.experimenter = slims_session_model.experimenter
            self.session_model.subject = slims_session_model.subject
            self.session_model.notes = slims_session_model.notes

            # update opto_model
            if self.opto_model.experiment_type in attachment_names:
                opto_attachment = attachments[attachment_names.index(self.opto_model.experiment_type)]
                self.opto_model = Optogenetics(**self.slims_client.fetch_attachment_content(opto_attachment).json())

            # update fip_model
            if self.fip_model.experiment_type in attachment_names:
                self.log.info(f"Applying fip model")
                fip_attachment = attachments[attachment_names.index(self.fip_model.experiment_type)]
                self.fip_model = FiberPhotometry(**self.slims_client.fetch_attachment_content(fip_attachment).json())
                # check if current stage is past stage_start
                self.fip_model.mode = None if STAGE_STARTS.index(self.trainer_state.stage.name) < \
                                              STAGE_STARTS.index(self.fip_model.stage_start) else self.fip_model.mode

            self.log.info(f"Mouse {mouse_id} curriculum loaded from Slims.")
            self._loaded_mouse_id = mouse_id

            return self.trainer_state, session

        except Exception as e:
            if 'No record found' in str(e):  # mouse doesn't exist
                raise KeyError(f"{mouse_id} is not in Slims. Double check id, and add to Slims if missing")
            else:
                Exception(f"Error loading mouse {mouse_id} curriculum loaded from Slims. {e}")

    def write_session_to_slims(self, mouse_id: str,
                               on_curriculum: bool,
                               foraging_efficiency: float,
                               finished_trials: int) -> DynamicForagingTrainerState:
        """
        Write next session to slims based on performance
        :param mouse_id: mouse id string to load from slims
        :param on_curriculum: if mouse is on curriculum or not
        :param foraging_efficiency: foraging efficiency of session
        :param finished_trials: finished trials in session
        """

        if self.metrics is not None and mouse_id == self._loaded_mouse_id:  # loaded mouse
            # add current session to metrics
            self.log.info("Constructing new metrics.")
            new_metrics = DynamicForagingMetrics(
                foraging_efficiency=self.metrics.foraging_efficiency + [foraging_efficiency],
                finished_trials=self.metrics.finished_trials + [finished_trials],
                session_total=self.metrics.session_total + 1,
                session_at_current_stage=self.metrics.session_at_current_stage + 1
            )

            if on_curriculum:
                # evaluating trainer state
                self.log.info("Generating next session stage.")
                next_trainer_state = Trainer(self.curriculum).evaluate(trainer_state=self.trainer_state,
                                                                       metrics=new_metrics)
            else:  # mouse is off curriculum so push trainer state used
                self.trainer_state.stage.task = self.task_logic
                next_trainer_state = self.trainer_state

            self.log.info("Writing trainer state to slims.")
            slims_model = self.trainer.write_data(subject_id=mouse_id,
                                                  curriculum=self.curriculum,
                                                  trainer_state=next_trainer_state,
                                                  date=datetime.now() if not hasattr(self, "session_model")
                                                  else self.session_model.date,
                                                  on_curriculum=on_curriculum)
            # add session model as an attachment
            self.slims_client.add_attachment_content(
                record=slims_model,
                name=AindBehaviorSessionModel.__name__,
                content=self.session_model.model_dump_json()
            )

            # add opto model if run
            if self.opto_model.laser_colors != []:
                self.slims_client.add_attachment_content(
                    record=slims_model,
                    name=self.opto_model.experiment_type,
                    content=self.opto_model.model_dump_json()
                )

            if self.fip_model.mode is not None:
                self.slims_client.add_attachment_content(
                    record=slims_model,
                    name=self.fip_model.experiment_type,
                    content=self.fip_model.model_dump_json()
                )

            self.log.info(f"Writing next session to Slims successful. "
                          f"Mouse {mouse_id} will run on {next_trainer_state.stage.name} next session.",
                          )

            # reset load state
            self.curriculum = None
            self.trainer_state = None
            self.metrics = None

        elif mouse_id != self._loaded_mouse_id:
            raise ValueError(f"Loaded mouse {self._loaded_mouse_id} does not match the input mouse id {mouse_id}")

        return self.trainer_state
