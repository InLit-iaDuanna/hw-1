import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface PhaseVisualizationProps {
  dataFile: string;
}

export const PhaseVisualization: React.FC<PhaseVisualizationProps> = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  // Simulated phase data (in real implementation, would load from CSV)
  const progress = frame / durationInFrames;

  // Simulate phase transitions
  const phases = [
    {name: 'stance_early', start: 0.0, end: 0.2, color: '#3B82F6'},
    {name: 'stance_late', start: 0.2, end: 0.4, color: '#1D4ED8'},
    {name: 'swing_thrust', start: 0.4, end: 0.6, color: '#10B981'},
    {name: 'swing_retract', start: 0.6, end: 0.8, color: '#059669'},
    {name: 'stance_early', start: 0.8, end: 1.0, color: '#3B82F6'},
  ];

  let currentPhase = phases[0];
  for (const phase of phases) {
    if (progress >= phase.start && progress < phase.end) {
      currentPhase = phase;
      break;
    }
  }

  // Simulate joint angles over time
  const hipAngle = interpolate(
    progress,
    [0, 0.25, 0.5, 0.75, 1.0],
    [10, -20, 15, -10, 10]
  );
  const kneeAngle = interpolate(
    progress,
    [0, 0.25, 0.5, 0.75, 1.0],
    [0, 5, 30, 10, 0]
  );
  const ankleAngle = interpolate(
    progress,
    [0, 0.25, 0.5, 0.75, 1.0],
    [-5, 0, 10, 5, -5]
  );

  // Contact state
  const leftContact = progress < 0.4 || progress > 0.8;
  const rightContact = progress >= 0.3 && progress < 0.7;

  return (
    <AbsoluteFill style={{backgroundColor: '#0F172A'}}>
      {/* Title */}
      <div
        style={{
          position: 'absolute',
          top: 40,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#F1F5F9',
          fontSize: 56,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        步态相位可视化
      </div>

      {/* Current phase indicator */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: currentPhase.color,
          fontSize: 36,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
          textTransform: 'uppercase',
        }}
      >
        {currentPhase.name.replace('_', ' ')}
      </div>

      {/* Phase timeline */}
      <div
        style={{
          position: 'absolute',
          top: 200,
          left: 100,
          right: 100,
          height: 60,
        }}
      >
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: '100%',
            display: 'flex',
          }}
        >
          {phases.map((phase, idx) => (
            <div
              key={idx}
              style={{
                flex: phase.end - phase.start,
                backgroundColor: phase.color,
                opacity: currentPhase.name === phase.name ? 1 : 0.4,
                border: '2px solid #0F172A',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 16,
                color: 'white',
                fontWeight: 'bold',
                fontFamily: 'Arial, sans-serif',
              }}
            >
              {phase.name.split('_')[1]}
            </div>
          ))}
        </div>
        {/* Progress indicator */}
        <div
          style={{
            position: 'absolute',
            left: `${progress * 100}%`,
            top: 0,
            bottom: 0,
            width: 4,
            backgroundColor: '#FBBF24',
            boxShadow: '0 0 20px rgba(251, 191, 36, 0.8)',
          }}
        />
      </div>

      {/* Joint angles */}
      <div
        style={{
          position: 'absolute',
          top: 320,
          left: 100,
          right: 100,
          height: 300,
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 40,
        }}
      >
        {/* Hip angle */}
        <AngleDisplay
          label="髋关节角度"
          angle={hipAngle}
          color="#EF4444"
          min={-30}
          max={30}
        />

        {/* Knee angle */}
        <AngleDisplay
          label="膝关节角度"
          angle={kneeAngle}
          color="#F59E0B"
          min={0}
          max={40}
        />

        {/* Ankle angle */}
        <AngleDisplay
          label="踝关节角度"
          angle={ankleAngle}
          color="#10B981"
          min={-15}
          max={15}
        />
      </div>

      {/* Contact state */}
      <div
        style={{
          position: 'absolute',
          top: 680,
          left: 100,
          right: 100,
          height: 200,
          display: 'flex',
          justifyContent: 'space-around',
          alignItems: 'center',
        }}
      >
        <ContactIndicator label="左脚接触" active={leftContact} />
        <ContactIndicator label="右脚接触" active={rightContact} />
      </div>

      {/* Time indicator */}
      <div
        style={{
          position: 'absolute',
          bottom: 40,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#94A3B8',
          fontSize: 24,
          fontFamily: 'monospace',
        }}
      >
        Time: {(progress * 12).toFixed(2)}s / 12.00s
      </div>
    </AbsoluteFill>
  );
};

// Angle display component
const AngleDisplay: React.FC<{
  label: string;
  angle: number;
  color: string;
  min: number;
  max: number;
}> = ({label, angle, color, min, max}) => {
  const normalized = ((angle - min) / (max - min)) * 100;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 20,
      }}
    >
      <div
        style={{
          color: '#F1F5F9',
          fontSize: 24,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        {label}
      </div>

      {/* Bar chart */}
      <div
        style={{
          position: 'relative',
          width: 80,
          height: 200,
          backgroundColor: '#1E293B',
          borderRadius: 40,
          overflow: 'hidden',
        }}
      >
        {/* Zero line */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: `${((0 - min) / (max - min)) * 100}%`,
            height: 2,
            backgroundColor: '#475569',
          }}
        />

        {/* Angle bar */}
        <div
          style={{
            position: 'absolute',
            left: 10,
            right: 10,
            bottom: 0,
            height: `${Math.max(0, normalized)}%`,
            backgroundColor: color,
            borderRadius: '35px 35px 0 0',
          }}
        />
      </div>

      {/* Value display */}
      <div
        style={{
          color: color,
          fontSize: 32,
          fontWeight: 'bold',
          fontFamily: 'monospace',
        }}
      >
        {angle.toFixed(1)}°
      </div>
    </div>
  );
};

// Contact indicator component
const ContactIndicator: React.FC<{label: string; active: boolean}> = ({
  label,
  active,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 20,
      }}
    >
      <div
        style={{
          width: 120,
          height: 120,
          borderRadius: '50%',
          backgroundColor: active ? '#10B981' : '#1E293B',
          border: active ? '6px solid #FBBF24' : '3px solid #475569',
          boxShadow: active
            ? '0 0 40px rgba(16, 185, 129, 0.8)'
            : 'none',
          transition: 'all 0.3s ease',
        }}
      />
      <div
        style={{
          color: active ? '#10B981' : '#94A3B8',
          fontSize: 28,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        {label}
      </div>
    </div>
  );
};
