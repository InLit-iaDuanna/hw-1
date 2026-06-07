import {Composition} from 'remotion';
import {PhaseVisualization} from './compositions/PhaseVisualization';
import {GaitComparison} from './compositions/GaitComparison';
import {FSMStateTransition} from './compositions/FSMStateTransition';
import {RollingFootAnimation} from './compositions/RollingFootAnimation';
import {DataDrivenExample} from './compositions/DataDrivenExample';
import {FrictionCompensation} from './compositions/FrictionCompensation';
import {TechnicalRoadmap} from './compositions/TechnicalRoadmap';
import {MotorDynamics} from './compositions/MotorDynamics';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="FSMStateTransition"
        component={FSMStateTransition}
        durationInFrames={240}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          phases: ['stance_early', 'stance_late', 'swing_thrust', 'swing_retract'],
        }}
      />
      <Composition
        id="RollingFootAnimation"
        component={RollingFootAnimation}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          dataFile: '../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv',
        }}
      />
      <Composition
        id="PhaseVisualization"
        component={PhaseVisualization}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          dataFile: '../v13_6_event_driven_fsm/out/v13_6_baseline_data.csv',
        }}
      />
      <Composition
        id="GaitComparison"
        component={GaitComparison}
        durationInFrames={360}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          v10Data: '../v10_rolling_foot_biomimetic_gait/out/v10_rolling_foot_walk_data.csv',
          v13Data: '../v13_6_event_driven_fsm/out/v13_6_baseline_data.csv',
        }}
      />
      <Composition
        id="DataDrivenExample"
        component={DataDrivenExample}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          dataFile: 'data/v10_data.json',
        }}
      />
      <Composition
        id="FrictionCompensation"
        component={FrictionCompensation}
        durationInFrames={360}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          showComparison: true,
        }}
      />
      <Composition
        id="TechnicalRoadmap"
        component={TechnicalRoadmap}
        durationInFrames={450}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          startVersion: 1,
          endVersion: 25,
        }}
      />
      <Composition
        id="MotorDynamics"
        component={MotorDynamics}
        durationInFrames={360}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          showFailureBand: true,
        }}
      />
    </>
  );
};
