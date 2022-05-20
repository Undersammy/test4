@router.get("/table_values/{date_1}/{date_2}", name="Data for table values")
def get_params(date_1, date_2):
    conn = sqlite3.connect('MSDopros.db')
    cursor = conn.cursor()
    table_values = cursor.execute("select Stat, UTC, Idle, Repr, DILght, Card from IdlePow WHERE "
                                  "Stat ==4 OR Stat ==8 OR Stat ==9 "
                                  "AND UTC >=? "
                                  "AND UTC <=? ", (date_1, date_2)).fetchall()
    if not table_values:
        raise HTTPException(status_code=404, detail="Данные не найдены")
    conn.close()

    # time_1 = datetime.strptime(date_1, "%Y-%m-%dT%H:%M:%S")
    # time_2 = datetime.strptime(date_2, "%Y-%m-%dT%H:%M:%S")
    # time_interval = (time_2 - time_1)

    return {"res": calculate_data(table_values)}


def calculate_data(table_values):
    all_time = 0
    new_res = {}
    operator_cards = []
    i = 1

    for table_value in table_values:
        all_time += 1
        operator_cards.append(table_value[4])
        stat = table_value[0]

        if stat == 8 or stat == 9:
            if stat not in new_res:
                new_res[stat] = {"time": 0, "id": 1, "reasons": {}}
            new_res[stat]["time"] += 1
            new_res[stat]["id"] += 1
            reason = table_value[3] if stat == 8 else table_value[2]
            if reason not in new_res[stat]["reasons"]:
                new_res[stat]["reasons"][reason] = {"time": 1, "id": 1, "operator_card": table_value[4]}
                continue
            new_res[stat]["reasons"][reason]["time"] += 1
            new_res[stat]["reasons"][reason]["id"] += 1
            new_res[stat]["reasons"][reason]["operator_card"] = table_value[4]
            continue

        if stat not in new_res:
            new_res[stat] = {"time": 1, "id": 1, "operator_card": table_value[4]}
            continue
        new_res[stat]["time"] += 1
        new_res[stat]["id"] += 1
        new_res[stat]["operator_card"] = table_value[4]

    session = connect_db()
    operators = session.query(Operator).filter(Operator.card.in_(operator_cards)).all()
    session.close()

    operators_card_dict: dict[str, Operator] = {operator.card: operator for operator in operators}

    res = []
    for state, value in new_res.items():
        new_value = {
            "id": i,
            "state": state,
            "idle": 0,
            "repr": 0,
            "time": value["time"],
            "percent": format((value["time"] / all_time) * 100, ".2f")
        }
        if state not in [8, 9]:
            operator = operators_card_dict.get(value["operator_card"])
            if operator:
                new_value["operator"] = operator.username
            else:
                new_value["operator"] = "нет данных об имени"
            res.append(new_value)
        else:
            for k, v in value["reasons"].items():
                new_state_value = dict(new_value)
                new_state_value["percent"] = format((v["time"] / all_time) * 100, ".2f")
                new_state_value["time"] = v["time"]
                key = "repr" if state == 8 else "idle"
                new_state_value[key] = k
                operator = operators_card_dict.get(v["operator_card"])
                if operator:
                    new_value["operator"] = operator.username
                else:
                    new_value["operator"] = "нет данных об имени"
                res.append(new_state_value)
    return res