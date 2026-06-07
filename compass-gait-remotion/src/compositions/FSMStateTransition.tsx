import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface FSMStateTransitionProps {
  phases: string[];
}

export const FSMStateTransition: React.FC<FSMStateTransitionProps> = ({
  phases,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Define phase colors and positions
  const phaseConfig = {
    stance_early: {color: '#3B82F6', label: 'Stance Early', x: 300, y: 200},
    stance_late: {color: '#1D4ED8', label: 'Stance Late', x: 700, y: 200},
    swing_thrust: {color: '#10B981', label: 'Swing Thrust', x: 300, y: 600},
    swing_retract: {color: '#059669', label: 'Swing Retract', x: 700, y: 600},
  };

  // Phase transition timing (30 frames per phase)
  const phaseDuration = 60;
  const currentPhaseIndex = Math.floor(frame / phaseDuration) % 4;
  const phaseProgress = (frame % phaseDuration) / phaseDuration;

  const phaseOrder = [
    'stance_early',
    'stance_late',
    'swing_thrust',
    'swing_retract',
  ];
  const currentPhase = phaseOrder[currentPhaseIndex];

  // Spring animation for active state
  const scale = spring({
    frame: frame % phaseDuration,
    fps,
    config: {
      damping: 10,
      stiffness: 100,
    },
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#0F172A'}}>
      {/* Title */}
      <div
        style={{
          position: 'absolute',
          top: 60,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#F1F5F9',
          fontSize: 64,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        V13.6 FSM 四相位状态机
      </div>

      {/* Phase nodes */}
      {Object.entries(phaseConfig).map(([phase, config]) => {
        const isActive = phase === currentPhase;
        const nodeScale = isActive ? 1 + scale * 0.2 : 1;

        return (
          <div
            key={phase}
            style={{
              position: 'absolute',
              left: config.x,
              top: config.y,
              transform: `translate(-50%, -50%) scale(${nodeScale})`,
              transition: 'all 0.3s ease',
            }}
          >
            {/* Circle */}
            <div
              style={{
                width: 180,
                height: 180,
                borderRadius: '50%',
                backgroundColor: config.color,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: isActive ? '6px solid #FBBF24' : '3px solid #475569',
                boxShadow: isActive
                  ? '0 0 40px rgba(251, 191, 36, 0.8)'
                  : '0 0 20px rgba(0, 0, 0, 0.5)',
              }}
            >
              <div
                style={{
                  textAlign: 'center',
                  color: 'white',
                  fontFamily: 'Arial, sans-serif',
                }}
              >
                <div style={{fontSize: 20, fontWeight: 'bold'}}>
                  {config.label}
                </div>
                {isActive && (
                  <div style={{fontSize: 16, marginTop: 8}}>
                    {Math.round(phaseProgress * 100)}%
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}

      {/* Arrows between phases */}
      {/* Stance Early -> Stance Late */}
      <Arrow
        from={{x: 400, y: 200}}
        to={{x: 600, y: 200}}
        active={currentPhase === 'stance_early'}
        label="u ≥ 0.5"
      />

      {/* Stance Late -> Swing Thrust */}
      <Arrow
        from={{x: 700, y: 300}}
        to={{x: 300, y: 500}}
        active={currentPhase === 'stance_late'}
        label="接触切换"
      />

      {/* Swing Thrust -> Swing Retract */}
      <Arrow
        from={{x: 400, y: 600}}
        to={{x: 600, y: 600}}
        active={currentPhase === 'swing_thrust'}
        label="u ≥ 0.5"
      />

      {/* Swing Retract -> Stance Early */}
      <Arrow
        from={{x: 300, y: 500}}
        to={{x: 300, y: 300}}
        active={currentPhase === 'swing_retract'}
        label="接触切换"
      />

      {/* Legend */}
      <div
        style={{
          position: 'absolute',
          bottom: 60,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          gap: 60,
          color: '#F1F5F9',
          fontSize: 24,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: '50%',
              backgroundColor: '#3B82F6',
            }}
          />
          <span>支撑相</span>
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: '50%',
              backgroundColor: '#10B981',
            }}
          />
          <span>摆动相</span>
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
          <div
            style={{
              width: 30,
              height: 6,
              backgroundColor: '#FBBF24',
            }}
          />
          <span>当前状态</span>
        </div>
      </div>

      {/* Frame counter */}
      <div
        style={{
          position: 'absolute',
          top: 20,
          right: 40,
          color: '#94A3B8',
          fontSize: 20,
          fontFamily: 'monospace',
        }}
      >
        Frame: {frame}
      </div>
    </AbsoluteFill>
  );
};

// Arrow component
const Arrow: React.FC<{
  from: {x: number; y: number};
  to: {x: number; y: number};
  active: boolean;
  label: string;
}> = ({from, to, active, label}) => {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx) * (180 / Math.PI);

  const midX = (from.x + to.x) / 2;
  const midY = (from.y + to.y) / 2;

  return (
    <>
      {/* Arrow line */}
      <div
        style={{
          position: 'absolute',
          left: from.x,
          top: from.y,
          width: length,
          height: active ? 4 : 2,
          backgroundColor: active ? '#FBBF24' : '#475569',
          transformOrigin: '0 50%',
          transform: `rotate(${angle}deg)`,
          boxShadow: active ? '0 0 10px rgba(251, 191, 36, 0.8)' : 'none',
        }}
      >
        {/* Arrowhead */}
        <div
          style={{
            position: 'absolute',
            right: -10,
            top: '50%',
            width: 0,
            height: 0,
            borderLeft: `10px solid ${active ? '#FBBF24' : '#475569'}`,
            borderTop: '6px solid transparent',
            borderBottom: '6px solid transparent',
            transform: 'translateY(-50%)',
          }}
        />
      </div>

      {/* Label */}
      <div
        style={{
          position: 'absolute',
          left: midX,
          top: midY - 30,
          transform: 'translateX(-50%)',
          color: active ? '#FBBF24' : '#94A3B8',
          fontSize: 18,
          fontFamily: 'Arial, sans-serif',
          fontWeight: active ? 'bold' : 'normal',
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </div>
    </>
  );
};
