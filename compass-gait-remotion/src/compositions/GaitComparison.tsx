import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface GaitComparisonProps {
  v10Data: string;
  v13Data: string;
}

export const GaitComparison: React.FC<GaitComparisonProps> = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const progress = frame / durationInFrames;

  // V10 characteristics (PD control with rolling foot)
  const v10Metrics = {
    success: true,
    forwardDistance: 4.85,
    alternations: 11,
    inputEnergy: 15.2,
    cot: 0.065,
    successRate: 16.7, // From slice C
  };

  // V13.6 characteristics (FSM control)
  const v13Metrics = {
    success: true,
    forwardDistance: 4.86,
    alternations: 11,
    inputEnergy: 17.45,
    cot: 0.072,
    successRate: 11.1, // From slice C
  };

  // Animate comparison bars
  const v10Progress = interpolate(progress, [0, 0.5], [0, 1], {
    extrapolateRight: 'clamp',
  });
  const v13Progress = interpolate(progress, [0.5, 1.0], [0, 1], {
    extrapolateLeft: 'clamp',
  });

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
        步态控制方案对比
      </div>

      {/* Subtitle */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#94A3B8',
          fontSize: 32,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        V10 PD控制 vs V13.6 FSM事件驱动
      </div>

      {/* Split view */}
      <div
        style={{
          position: 'absolute',
          top: 200,
          left: 0,
          right: 0,
          bottom: 120,
          display: 'flex',
        }}
      >
        {/* V10 Section */}
        <div
          style={{
            flex: 1,
            borderRight: '2px solid #475569',
            padding: 40,
            display: 'flex',
            flexDirection: 'column',
            gap: 30,
          }}
        >
          <div
            style={{
              textAlign: 'center',
              color: '#3B82F6',
              fontSize: 42,
              fontWeight: 'bold',
              fontFamily: 'Arial, sans-serif',
            }}
          >
            V10 足踝滚动
          </div>

          <div
            style={{
              color: '#94A3B8',
              fontSize: 20,
              fontFamily: 'Arial, sans-serif',
              lineHeight: 1.8,
            }}
          >
            <div>• PD 控制律</div>
            <div>• 被动踝关节滚动</div>
            <div>• 脚跟-足底-脚趾接触</div>
            <div>• 简单可靠</div>
          </div>

          <MetricBar
            label="前进距离"
            value={v10Metrics.forwardDistance}
            max={5}
            unit="m"
            progress={v10Progress}
            color="#3B82F6"
          />

          <MetricBar
            label="输入能量"
            value={v10Metrics.inputEnergy}
            max={20}
            unit="J"
            progress={v10Progress}
            color="#3B82F6"
          />

          <MetricBar
            label="CoT"
            value={v10Metrics.cot}
            max={0.1}
            unit=""
            progress={v10Progress}
            color="#3B82F6"
          />

          <MetricBar
            label="切片C成功率"
            value={v10Metrics.successRate}
            max={20}
            unit="%"
            progress={v10Progress}
            color="#3B82F6"
          />
        </div>

        {/* V13.6 Section */}
        <div
          style={{
            flex: 1,
            padding: 40,
            display: 'flex',
            flexDirection: 'column',
            gap: 30,
          }}
        >
          <div
            style={{
              textAlign: 'center',
              color: '#10B981',
              fontSize: 42,
              fontWeight: 'bold',
              fontFamily: 'Arial, sans-serif',
            }}
          >
            V13.6 FSM控制
          </div>

          <div
            style={{
              color: '#94A3B8',
              fontSize: 20,
              fontFamily: 'Arial, sans-serif',
              lineHeight: 1.8,
            }}
          >
            <div>• 四相位 FSM</div>
            <div>• 事件驱动切换</div>
            <div>• 能量整形 + PD</div>
            <div>• 可读可调</div>
          </div>

          <MetricBar
            label="前进距离"
            value={v13Metrics.forwardDistance}
            max={5}
            unit="m"
            progress={v13Progress}
            color="#10B981"
          />

          <MetricBar
            label="输入能量"
            value={v13Metrics.inputEnergy}
            max={20}
            unit="J"
            progress={v13Progress}
            color="#10B981"
          />

          <MetricBar
            label="CoT"
            value={v13Metrics.cot}
            max={0.1}
            unit=""
            progress={v13Progress}
            color="#10B981"
          />

          <MetricBar
            label="切片C成功率"
            value={v13Metrics.successRate}
            max={20}
            unit="%"
            progress={v13Progress}
            color="#10B981"
          />
        </div>
      </div>

      {/* Summary */}
      <div
        style={{
          position: 'absolute',
          bottom: 40,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#F1F5F9',
          fontSize: 24,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        两种方案均为准被动控制，各有优势
      </div>
    </AbsoluteFill>
  );
};

// Metric bar component
const MetricBar: React.FC<{
  label: string;
  value: number;
  max: number;
  unit: string;
  progress: number;
  color: string;
}> = ({label, value, max, unit, progress, color}) => {
  const barWidth = (value / max) * 100 * progress;

  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 10}}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          color: '#F1F5F9',
          fontSize: 20,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        <span>{label}</span>
        <span style={{fontWeight: 'bold', color}}>
          {(value * progress).toFixed(2)} {unit}
        </span>
      </div>

      <div
        style={{
          position: 'relative',
          width: '100%',
          height: 30,
          backgroundColor: '#1E293B',
          borderRadius: 15,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: `${barWidth}%`,
            height: '100%',
            backgroundColor: color,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
    </div>
  );
};
