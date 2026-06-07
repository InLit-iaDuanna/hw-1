import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface DataPoint {
  time: number;
  hip_x: number;
  hip_z: number;
  left_hip: number;
  left_knee: number;
  left_ankle: number;
  right_hip: number;
  right_knee: number;
  right_ankle: number;
  left_contact: boolean;
  right_contact: boolean;
  mode?: string;
}

interface DataDrivenExampleProps {
  dataFile: string;
}

export const DataDrivenExample: React.FC<DataDrivenExampleProps> = ({
  dataFile,
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const [data, setData] = useState<DataPoint[]>([]);
  const [handle] = useState(() => delayRender());

  useEffect(() => {
    // 尝试加载数据文件
    fetch(staticFile(dataFile))
      .then((res) => res.json())
      .then((jsonData: DataPoint[]) => {
        setData(jsonData);
        continueRender(handle);
      })
      .catch((error) => {
        console.error('Failed to load data:', error);
        // 如果加载失败，使用模拟数据
        const simulatedData: DataPoint[] = [];
        for (let i = 0; i < 100; i++) {
          simulatedData.push({
            time: i * 0.1,
            hip_x: i * 0.05,
            hip_z: 1.0,
            left_hip: Math.sin(i * 0.1) * 20,
            left_knee: Math.max(0, Math.sin(i * 0.15) * 30),
            left_ankle: Math.sin(i * 0.12) * 10,
            right_hip: Math.sin((i + 50) * 0.1) * 20,
            right_knee: Math.max(0, Math.sin((i + 50) * 0.15) * 30),
            right_ankle: Math.sin((i + 50) * 0.12) * 10,
            left_contact: i % 60 < 30,
            right_contact: i % 60 >= 30,
          });
        }
        setData(simulatedData);
        continueRender(handle);
      });
  }, [dataFile, handle]);

  // 如果数据还在加载
  if (data.length === 0) {
    return null;
  }

  // 计算当前帧对应的数据索引
  const progress = frame / durationInFrames;
  const dataIndex = Math.floor(progress * (data.length - 1));
  const currentData = data[dataIndex];

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
        数据驱动动画示例
      </div>

      {/* Data info */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#94A3B8',
          fontSize: 24,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        已加载 {data.length} 个数据点 | 当前索引: {dataIndex}
      </div>

      {/* Joint angles display */}
      <div
        style={{
          position: 'absolute',
          top: 250,
          left: 100,
          right: 100,
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 40,
        }}
      >
        <JointAngleCard label="左髋" angle={currentData.left_hip} color="#EF4444" />
        <JointAngleCard label="左膝" angle={currentData.left_knee} color="#F59E0B" />
        <JointAngleCard label="左踝" angle={currentData.left_ankle} color="#10B981" />
        <JointAngleCard label="右髋" angle={currentData.right_hip} color="#EF4444" />
        <JointAngleCard label="右膝" angle={currentData.right_knee} color="#F59E0B" />
        <JointAngleCard label="右踝" angle={currentData.right_ankle} color="#10B981" />
      </div>

      {/* Contact state */}
      <div
        style={{
          position: 'absolute',
          bottom: 200,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          gap: 100,
        }}
      >
        <ContactState label="左脚" active={currentData.left_contact} />
        <ContactState label="右脚" active={currentData.right_contact} />
      </div>

      {/* Timeline */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          left: 100,
          right: 100,
          color: '#94A3B8',
          fontSize: 20,
          textAlign: 'center',
          fontFamily: 'monospace',
        }}
      >
        Time: {currentData.time.toFixed(3)}s
        {currentData.mode && ` | Mode: ${currentData.mode}`}
      </div>
    </AbsoluteFill>
  );
};

// Joint angle card component
const JointAngleCard: React.FC<{
  label: string;
  angle: number;
  color: string;
}> = ({label, angle, color}) => {
  return (
    <div
      style={{
        backgroundColor: '#1E293B',
        borderRadius: 16,
        padding: 30,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 20,
      }}
    >
      <div
        style={{
          color: '#F1F5F9',
          fontSize: 28,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        {label}
      </div>
      <div
        style={{
          color: color,
          fontSize: 48,
          fontWeight: 'bold',
          fontFamily: 'monospace',
        }}
      >
        {angle.toFixed(1)}°
      </div>
    </div>
  );
};

// Contact state component
const ContactState: React.FC<{label: string; active: boolean}> = ({
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
          width: 100,
          height: 100,
          borderRadius: '50%',
          backgroundColor: active ? '#10B981' : '#1E293B',
          border: active ? '5px solid #FBBF24' : '3px solid #475569',
          boxShadow: active ? '0 0 30px rgba(16, 185, 129, 0.8)' : 'none',
        }}
      />
      <div
        style={{
          color: active ? '#10B981' : '#94A3B8',
          fontSize: 24,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        {label}
      </div>
    </div>
  );
};
