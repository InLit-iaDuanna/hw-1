import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface MotorDynamicsProps {
  showFailureBand?: boolean;
}

/**
 * V16 电机动力学与失败带分析
 * 展示电机性能限制与失败带可视化
 */
export const MotorDynamics: React.FC<MotorDynamicsProps> = ({
  showFailureBand = true,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const progress = frame / durationInFrames;

  // 电机规格
  const motorSpecs = {
    name: 'Maxon EC45',
    nominalTorque: 0.134, // Nm
    peakTorque: 0.561, // Nm
    nominalSpeed: 426, // rad/s
    peakSpeed: 523, // rad/s
    resistance: 1.16, // Ohm
    torqueConstant: 0.0335, // Nm/A
  };

  // 失败带数据（简化版）
  const failureBandData = [
    {hip: -30, knee: 0, status: 'success', label: 'A'},
    {hip: -20, knee: 10, status: 'success', label: 'B'},
    {hip: -10, knee: 20, status: 'failure', label: 'C'},
    {hip: 0, knee: 30, status: 'failure', label: 'D'},
    {hip: 10, knee: 25, status: 'success', label: 'E'},
    {hip: 20, knee: 15, status: 'success', label: 'F'},
  ];

  // 当前高亮点
  const currentPointIndex = Math.floor(
    progress * (failureBandData.length - 1)
  );

  return (
    <AbsoluteFill style={{backgroundColor: '#0F172A'}}>
      {/* 标题 */}
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
        V16 电机动力学建模
      </div>

      {/* 副标题 */}
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
        Motor Dynamics & Failure Band Analysis
      </div>

      {/* 主内容区 */}
      <div
        style={{
          position: 'absolute',
          top: 220,
          left: 80,
          right: 80,
          bottom: 100,
          display: 'flex',
          gap: 40,
        }}
      >
        {/* 左侧：电机规格 */}
        <div
          style={{
            flex: 1,
            backgroundColor: '#1E293B',
            borderRadius: 20,
            padding: 40,
            border: '3px solid #3B82F6',
          }}
        >
          <div
            style={{
              color: '#3B82F6',
              fontSize: 36,
              fontWeight: 'bold',
              marginBottom: 30,
              textAlign: 'center',
              fontFamily: 'Arial, sans-serif',
            }}
          >
            电机规格
          </div>

          <div style={{display: 'flex', flexDirection: 'column', gap: 20}}>
            <SpecRow
              label="型号"
              value={motorSpecs.name}
              unit=""
              color="#F1F5F9"
            />
            <SpecRow
              label="额定扭矩"
              value={motorSpecs.nominalTorque.toFixed(3)}
              unit="Nm"
              color="#10B981"
            />
            <SpecRow
              label="峰值扭矩"
              value={motorSpecs.peakTorque.toFixed(3)}
              unit="Nm"
              color="#EF4444"
            />
            <SpecRow
              label="额定转速"
              value={motorSpecs.nominalSpeed.toFixed(0)}
              unit="rad/s"
              color="#10B981"
            />
            <SpecRow
              label="峰值转速"
              value={motorSpecs.peakSpeed.toFixed(0)}
              unit="rad/s"
              color="#EF4444"
            />
            <SpecRow
              label="电阻"
              value={motorSpecs.resistance.toFixed(2)}
              unit="Ω"
              color="#F59E0B"
            />
            <SpecRow
              label="扭矩常数"
              value={motorSpecs.torqueConstant.toFixed(4)}
              unit="Nm/A"
              color="#8B5CF6"
            />
          </div>

          {/* 电机示意图 */}
          <div
            style={{
              marginTop: 40,
              display: 'flex',
              justifyContent: 'center',
            }}
          >
            <MotorIcon progress={progress} />
          </div>
        </div>

        {/* 右侧：失败带可视化 */}
        <div
          style={{
            flex: 1.2,
            backgroundColor: '#1E293B',
            borderRadius: 20,
            padding: 40,
            border: '3px solid #F59E0B',
          }}
        >
          <div
            style={{
              color: '#F59E0B',
              fontSize: 36,
              fontWeight: 'bold',
              marginBottom: 30,
              textAlign: 'center',
              fontFamily: 'Arial, sans-serif',
            }}
          >
            失败带分析
          </div>

          {/* 失败带图表 */}
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: 500,
              backgroundColor: '#0F172A',
              borderRadius: 12,
              padding: 20,
            }}
          >
            {/* 坐标轴 */}
            <svg width="100%" height="100%">
              {/* X轴 */}
              <line
                x1="50"
                y1="450"
                x2="650"
                y2="450"
                stroke="#475569"
                strokeWidth="2"
              />
              {/* Y轴 */}
              <line
                x1="50"
                y1="50"
                x2="50"
                y2="450"
                stroke="#475569"
                strokeWidth="2"
              />

              {/* X轴标签 */}
              <text
                x="350"
                y="480"
                fill="#94A3B8"
                fontSize="16"
                textAnchor="middle"
                fontFamily="Arial, sans-serif"
              >
                Hip Angle (deg)
              </text>

              {/* Y轴标签 */}
              <text
                x="20"
                y="250"
                fill="#94A3B8"
                fontSize="16"
                textAnchor="middle"
                transform="rotate(-90, 20, 250)"
                fontFamily="Arial, sans-serif"
              >
                Knee Angle (deg)
              </text>

              {/* 数据点 */}
              {failureBandData.map((point, idx) => {
                const x = 50 + ((point.hip + 30) / 50) * 600;
                const y = 450 - (point.knee / 30) * 400;
                const isActive = idx <= currentPointIndex;
                const isCurrent = idx === currentPointIndex;

                return (
                  <g key={idx}>
                    {/* 连线 */}
                    {idx > 0 && isActive && (
                      <line
                        x1={
                          50 +
                          ((failureBandData[idx - 1].hip + 30) / 50) * 600
                        }
                        y1={
                          450 - (failureBandData[idx - 1].knee / 30) * 400
                        }
                        x2={x}
                        y2={y}
                        stroke={
                          point.status === 'success' ? '#10B981' : '#EF4444'
                        }
                        strokeWidth="3"
                        strokeDasharray={
                          point.status === 'failure' ? '5,5' : '0'
                        }
                      />
                    )}

                    {/* 点 */}
                    {isActive && (
                      <>
                        <circle
                          cx={x}
                          cy={y}
                          r={isCurrent ? 12 : 8}
                          fill={
                            point.status === 'success' ? '#10B981' : '#EF4444'
                          }
                          stroke="#F1F5F9"
                          strokeWidth={isCurrent ? 3 : 2}
                        />
                        <text
                          x={x}
                          y={y - 20}
                          fill="#F1F5F9"
                          fontSize="14"
                          textAnchor="middle"
                          fontWeight="bold"
                          fontFamily="Arial, sans-serif"
                        >
                          {point.label}
                        </text>
                      </>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>

          {/* 图例 */}
          <div
            style={{
              marginTop: 20,
              display: 'flex',
              justifyContent: 'center',
              gap: 40,
            }}
          >
            <Legend color="#10B981" label="成功区域" />
            <Legend color="#EF4444" label="失败带" />
          </div>
        </div>
      </div>

      {/* 底部说明 */}
      <div
        style={{
          position: 'absolute',
          bottom: 30,
          left: 80,
          right: 80,
          textAlign: 'center',
          color: '#94A3B8',
          fontSize: 20,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        电机性能限制影响步态稳定性 | V16 引入真实电机模型
      </div>
    </AbsoluteFill>
  );
};

// 规格行组件
const SpecRow: React.FC<{
  label: string;
  value: string;
  unit: string;
  color: string;
}> = ({label, value, unit, color}) => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 0',
        borderBottom: '1px solid #334155',
      }}
    >
      <span
        style={{
          color: '#94A3B8',
          fontSize: 18,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        {label}
      </span>
      <span
        style={{
          color: color,
          fontSize: 22,
          fontWeight: 'bold',
          fontFamily: 'monospace',
        }}
      >
        {value} {unit}
      </span>
    </div>
  );
};

// 电机图标组件
const MotorIcon: React.FC<{progress: number}> = ({progress}) => {
  const rotation = progress * 360 * 3; // 旋转3圈

  return (
    <svg width="150" height="150" viewBox="0 0 150 150">
      {/* 外壳 */}
      <rect
        x="25"
        y="40"
        width="100"
        height="70"
        rx="10"
        fill="#475569"
        stroke="#64748B"
        strokeWidth="3"
      />

      {/* 转子 */}
      <circle
        cx="75"
        cy="75"
        r="25"
        fill="#3B82F6"
        stroke="#60A5FA"
        strokeWidth="3"
        transform={`rotate(${rotation} 75 75)`}
      />

      {/* 转子标记 */}
      <line
        x1="75"
        y1="75"
        x2="75"
        y2="55"
        stroke="#F1F5F9"
        strokeWidth="4"
        strokeLinecap="round"
        transform={`rotate(${rotation} 75 75)`}
      />

      {/* 轴 */}
      <rect x="120" y="70" width="20" height="10" fill="#94A3B8" />

      {/* 接线端子 */}
      <circle cx="40" cy="110" r="4" fill="#EF4444" />
      <circle cx="50" cy="110" r="4" fill="#000000" />
    </svg>
  );
};

// 图例组件
const Legend: React.FC<{color: string; label: string}> = ({color, label}) => {
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 10}}>
      <div
        style={{
          width: 20,
          height: 20,
          borderRadius: '50%',
          backgroundColor: color,
        }}
      />
      <span
        style={{
          color: '#F1F5F9',
          fontSize: 18,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        {label}
      </span>
    </div>
  );
};
