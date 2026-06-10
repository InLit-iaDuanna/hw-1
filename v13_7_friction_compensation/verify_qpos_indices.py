import mujoco

xml_path = r"D:\Dunna\Documents\hw-1\v13_7_friction_compensation\out\v13_7_models\friction_comp_walker.xml"
model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)

print(f"nq={model.nq}, nv={model.nv}, nu={model.nu}")
print("\nJoint mapping:")
for j in range(model.njnt):
    name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j)
    jtype = model.jnt_type[j]
    qadr = model.jnt_qposadr[j]
    dadr = model.jnt_dofadr[j]
    print(f"{j:2d} {name:15s} type={jtype} qposadr={qadr} dofadr={dadr}")

mujoco.mj_resetData(model, data)
print(f"\nqpos after mj_resetData: {data.qpos.copy()}")
