import requests
from __src.config.config import RobotSkillConfig


def make_group_list_text(url):
    response = requests.get(f"{url}/env_entire")
    all = response.json()

    groups = all["objects_by_group"].keys()
    print(f"Groups found: {groups}")
    group_list_text = "[\n"
    for group in groups:
        group_list_text += f'    "{group}",\n'
    group_list_text += "]"
    return group_list_text


def make_object_text(url, object_name=None):
    response = requests.get(f"{url}/env_entire")
    all = response.json()

    objects_by_group = all["objects_by_group"]
    ungrouped_objects = all["ungrouped_objects"]

    total_object_text = "{{{{\n"
    for group_name, objects_list in objects_by_group.items():
        if objects_list:
            print(f"Group: {group_name}")
            for obj in objects_list:
                if object_name is not None:
                    if obj != object_name:
                        continue
                object_text = (
                    f'"object_name": "{obj}", "object_in_group": "{group_name}"\n'
                )
                total_object_text += object_text

    total_object_text += "}}}}"
    if ungrouped_objects:
        raise ValueError("There are ungrouped objects in the environment.")

    return total_object_text


def make_skill_text(config_skills: list[RobotSkillConfig]) -> str:
    skill_text_list = []
    for robot_skill in config_skills:

        skill_text = f"from {robot_skill.name}.skills import "
        for skill in robot_skill.skills:
            skill_text += f"{skill}"
            if skill != robot_skill.skills[-1]:
                skill_text += ", "
        skill_text_list.append(skill_text)

    return "\n".join(skill_text_list)
