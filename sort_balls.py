from graphics import Canvas
import random
from timeit import default_timer as timer
from datetime import timedelta
from database import db_get, db_set, db_list
import string

# just for debugging
# db_set("lvl_1", None)

EASY = "EASY"
NORMAL = "NORMAL"

CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 600

SIZE = 40
TUBE_PADDING = 20
TUBE_RIM = 10

TUBE_COLOR = "#333"
# helpers for rim and outline
DR1 = TUBE_RIM - 3
DR2 = TUBE_RIM + 3

BALLS_PER_TUBE = 4
COLORS_AVAILABLE = ["#029E73", "#D55E00", "#CC78BC", "#CA9161", "#FBAFE4", "#949494", "#ECE133", "#56B4E9", "#0173B2", "#DE8F05"]
MAX_LVL = 8

HOF_MAX_LEN = 10

def main():
    canvas = Canvas(CANVAS_WIDTH, CANVAS_HEIGHT)
    total_time = 0

    name = ''
    intro(canvas, MAX_LVL)
    rules, lvl = choose_rules(canvas)
    score = 0

    while lvl <= MAX_LVL:
        moves = 0
        tubes, level_text, score_text, moves_text, restart_lvl = init_lvl(canvas, rules, lvl, MAX_LVL, score, moves)

        selection_seq = 1
        tube1 = None
        tube2 = None
        selected_color = None
        start = timer()
        hof = []

        while True:
            canvas.wait_for_click()
            x, y = get_click(canvas)
            # restart requested
            if restart_lvl in canvas.find_overlapping(x, y, x, y):
                moves = 0
                tubes, level_text, score_text, moves_text, restart_lvl = init_lvl(canvas, rules, lvl, MAX_LVL, score, moves)
                tube1 = None
                tube2 = None
                selected_color = None
                hof = []
                start = timer()

            selection_seq, tube1, tube2, selected_color = get_user_choice(canvas, tubes, selection_seq, tube1, tube2, selected_color, rules, x, y)
            if selection_seq == 2 and tube2 != None:
                # move ball
                deselect_ball(canvas, tube1)
                move_ball(tube1, tube2, canvas)
                moves += 1
                canvas.change_text(score_text, get_score_text(score))
                canvas.change_text(moves_text, get_moves_text(moves))
                # reset to next selection
                if not finished(tubes):
                    tube1 = None
                    tube2 = None
                    selected_color = None
                    selection_seq = 1
                else:
                    end = timer()
                    time_taken = end - start
                    total_time += time_taken
                    hof_idx, hof, hof_db_key = qualify_to_hof(lvl, rules, time_taken)
                    if hof_idx < HOF_MAX_LEN:
                        if name == "":
                            name = get_user_name(canvas, name)
                        hof = update_hof(hof_db_key, hof, hof_idx, time_taken, name)
                   
                    if lvl < MAX_LVL:
                        score += congratulations(canvas, "Nice, now try next level :)", lvl, score, moves, time_taken, hof, rules)
                    lvl += 1
                    break
    congratulations(canvas, "Congratulations! YOU WON !!!", lvl, score, moves, total_time, hof, rules)

def get_click(canvas):
    x = 0
    y = 0
    click = canvas.get_last_click()
    if click != None:
        x = click[0]
        y = click[1]
    return (x, y)

def update_hof(key, hof, idx, time_taken, name):
    save = True
    if name == "":
        name = "*** YOU ***"
        save = False
    hof.insert(idx, {'time': time_taken, 'name': name})
    hof = hof[: HOF_MAX_LEN]
    if save:
        db_set(key, hof)
    return hof

def sort_by_time(entry):
    return entry['time']

def get_hof(lvl, rules):
    key = f"lvl_{lvl}"
    if rules == NORMAL:
        key += "-NORMAL"
    hof = db_get(key)
    if hof == None:
        hof = []
    hof.sort(key=sort_by_time)
    return (hof, key)

def qualify_to_hof(lvl, rules, time_taken):
    hof, key = get_hof(lvl, rules)
    # we either find a place in top 10 (HOF_MAX_LEN) or list is not full yet
    # so we set default value for idx (position in HoF) to lesser of those two values
    # let's first check if we managed to be ranked among top HOF_MAX_LEN participants
    idx = min(len(hof), HOF_MAX_LEN)
    for i in range(len(hof)):
        entry = hof[i]
        if entry['time'] > time_taken and i < HOF_MAX_LEN:
            idx = i # this is opr position
            break
    # idx == HOF_MAX_LEN means user didn't make it :(
    return (idx, hof, key)

def get_text_width(txt, size):
    return len(txt) * size * 17/28

def get_user_name(canvas, name):
    w = 500
    h = 200
    x = CANVAS_WIDTH / 2 
    y = CANVAS_HEIGHT /2
    text_x1 = x - (10*30) / 2


    dialog_shapes = []
    dialog_shapes.append(canvas.create_rectangle(x - w / 2, y, x + w / 2, y + h, "white", "black"))
    dialog_shapes.append(canvas.create_text(x, y + 30, "Please enter your name and hit [Enter]", anchor="center", font_size=28) )
    dialog_shapes.append(canvas.create_rectangle(text_x1, y + 100, text_x1 + 10 *30, y + 140, "black"))
    name_obj = canvas.create_text(text_x1 + 10, y + 120, name, anchor="w", font_size = 28, color="white", font="Courier")
    text_w = get_text_width(name, 28)
    cursor = canvas.create_rectangle(text_x1 + 10 + text_w, y+110, text_x1 + 10 + text_w + 4, y+110 + 28*0.75, "white")
    dialog_shapes.append(name_obj)
    dialog_shapes.append(cursor)

    t0 = timer()
    show_cursor = True
    while True:
        # cursor blinking
        t1 = timer()
        if t1 - t0 > 0.5:
            t0 = t1
            show_cursor = not show_cursor
            canvas.set_hidden(cursor, not show_cursor)

        key = canvas.get_last_key_press()
        if key != None:
            if len(key) == 1 and len(name) < 16:
                name += key
            elif key == "Backspace":
                name = name[:-1]
            if key == "Enter":
                break
            canvas.change_text(name_obj, name)
            text_w = get_text_width(name, 28)
            canvas.moveto(cursor, text_x1 + 10 + text_w, y + 110)

    # cleanup
    for obj in dialog_shapes:
        canvas.delete(obj)

    return name

def print_hof(canvas, y, lvl, hof, time, rules):
    x = CANVAS_WIDTH /2
    canvas.create_text(x, y, f"Level {lvl} Hall of Fame ({rules})", font_size = 24, anchor="center")
    y = y + 30
    for i in range(len(hof)):
        entry = hof[i]
        y += 25
        if entry['time'] == time:
            color = COLORS_AVAILABLE[1]
        else:
            color = "black"
        canvas.create_text(x * 2/3, y, f"{i + 1} - {str(timedelta(seconds=entry['time']))[:-3]} - {entry['name']}", font_size = 18, color=color)
    
def intro(canvas, MAX_LVL):
    x = CANVAS_WIDTH /2
    canvas.create_text(x, CANVAS_HEIGHT * 1/3, "Sort balls by color", font_size = 72, anchor = "center", color = COLORS_AVAILABLE[0])
    canvas.create_text(x, CANVAS_HEIGHT * 2/3, f"There are {MAX_LVL} levels of increasing difficulty", font_size = 24, anchor = "center", color = COLORS_AVAILABLE[8])
    canvas.create_text(x, CANVAS_HEIGHT * 3/4, f"Click anywhere to start", font_size = 24, anchor = "center", color = COLORS_AVAILABLE[1])

    yy = CANVAS_HEIGHT - 30
    MAX_TEXT_LEN = 75
    txt = "getting Hall of Fame..."
    hof_obj = canvas.create_text(10, yy, f"{txt: ^75}", font_size = 22, font="Courier", color="#333", anchor="w")
    hof_text = f"{' ' * MAX_TEXT_LEN}Hall of Fame :::  {get_hof_text(EASY)}  :::  {get_hof_text(NORMAL)}"
    marquee(canvas, 10, yy, hof_obj, hof_text, MAX_TEXT_LEN, 0.15)

def marquee(canvas, x, y, txt_obj, full_txt, max_len, delay):
    idx = 0
    dx = 0
    # pixel scroll
    txt = full_txt[idx:idx + max_len] 
    while True:
        dx += 3
        if dx > 13: # reset when it ends
            dx = 0
            idx += 1
            if idx == len(full_txt):
                idx = 0
            txt = full_txt[idx:idx + max_len + 1] # we need one more letter for smoth animation

        canvas.delete(txt_obj)
        txt_obj = canvas.create_text(x - dx, y, txt, font_size = 22, font="Courier", color="#333", anchor="w")
        time.sleep(0.001)

    # letter scroll
    # while True:
    #     # scroll by letters as scrolling by pixels with canvas.moveto() doesn't seem to work for text objects :(
    #     idx += 1
    #     if idx == len(full_txt):
    #         idx = 0
    #     txt = full_txt[idx:idx + max_len - 1]
    #     canvas.change_text(txt_obj, txt)
    #     time.sleep(delay)
        if canvas.get_last_click() != None:
            break

def get_hof_text(rules):
    txt = f"{rules}: "
    for lvl in range(MAX_LVL):
        hof, key = get_hof(lvl + 1, rules)
        if len(hof) > 0:
            txt += f"lvl {lvl + 1}: "
            for i in range(min(len(hof), 3)):
                entry = hof[i]
                txt += f"{i + 1} - {str(timedelta(seconds=entry['time']))[:-3]} - {entry['name']}  ...  "
    return txt

def get_score_text(score):
    return f"Score: {score}"

def get_moves_text(moves):
    return f"Moves: {moves}"

def finished(tubes):
    for tube in tubes:
        colors = []
        for ball in tube['balls']:
            colors.append(ball['color'])
        count = len(colors)
        tube_finished = count == 0 or (count > 0 and not random_enough(colors)) 
        if not tube_finished:
            return False
    return True

def choose_rules(canvas):
    canvas.clear()
    canvas.create_text(CANVAS_WIDTH / 2, CANVAS_HEIGHT * 1 / 5, "Choose rules", anchor="center", font_size = 32)

    y = CANVAS_HEIGHT / 2 - 50
    x_easy = CANVAS_WIDTH * 1/4
    x_normal = CANVAS_WIDTH * 3/4

    easy = canvas.create_rectangle(x_easy - 80, y - 30, x_easy + 80, y + 30, COLORS_AVAILABLE[0], "black")
    normal = canvas.create_rectangle(x_normal - 80, y - 30, x_normal + 80, y + 30, COLORS_AVAILABLE[1], "black")
    canvas.create_text(x_easy, y, "EASY", anchor="center", font_size = 28)
    canvas.create_text(x_normal, y, "NORMAL", anchor="center", font_size = 28)

    y += 80
    canvas.create_text(x_easy, y, "You can freely move the balls", anchor="center", font_size = 22)
    canvas.create_text(x_easy, y + 25, "wherever there is space available", anchor="center", font_size = 22)
    
    canvas.create_text(x_normal, y, "You can only move balls to places", anchor="center", font_size = 22)
    canvas.create_text(x_normal, y + 25, "where the last ball is the same", anchor="center", font_size = 22)
    canvas.create_text(x_normal, y + 50, "color as the currently selected one,", anchor="center", font_size = 22)
    canvas.create_text(x_normal, y + 75, "or to an empty tube", anchor="center", font_size = 22)
    
    canvas.create_text(CANVAS_WIDTH / 2, y + 170, "You can also start directly from one of the levels:", anchor="center", font_size = 22)
    
    easy_levels = draw_levels(canvas, x_easy, y + 200, COLORS_AVAILABLE[0])
    normal_levels = draw_levels(canvas, x_normal, y + 200, COLORS_AVAILABLE[1])

    while True:
        canvas.wait_for_click()
        x, y = get_click(canvas)
        objs = canvas.find_overlapping(x, y, x, y)
        lvl = get_clicked_lvl(easy_levels, objs)
        if lvl > 0:
            return (EASY, lvl)
        lvl = get_clicked_lvl(normal_levels, objs)
        if lvl > 0:
            return (NORMAL, lvl)

        if easy in objs:
            return (EASY , 1)
        elif normal in objs:
            return (NORMAL, 1)

def get_clicked_lvl(lst, objs):
    lvl = 0
    for obj in objs:
        try:
            lvl = lst.index(obj)
            return lvl + 1
        except ValueError:
            break
    return lvl

def draw_levels(canvas, x_center, y, color):
    lst = []
    btn_w = 40
    btn_h = 40
    x_start = x_center - (MAX_LVL * btn_w ) / 2
    for i in range(MAX_LVL):
        x = x_start + i* btn_w
        lst. append(canvas.create_rectangle(x, y, x + btn_w, y + 40, color, "black"))
        canvas.create_text(x + btn_w / 2, y + btn_h / 2, f"{i + 1}", anchor="center", font_size = 22) 
    return lst

def congratulations(canvas, text, lvl, score, moves, time, hof, rules):
    canvas.clear()
    canvas.create_text(CANVAS_WIDTH / 2, CANVAS_HEIGHT * 1 / 4, text, anchor="center", font_size = 32)
    lvl_score = max(0, lvl * 10 - moves)
    canvas.create_text(CANVAS_WIDTH / 2, CANVAS_HEIGHT * 1/3, f"Your time: {str(timedelta(seconds=time))[:-3]}", anchor="center", font_size = 22)
    canvas.create_text(CANVAS_WIDTH / 2, CANVAS_HEIGHT * 1/3 + 30 , f"Number of moves: {moves}", anchor="center", font_size = 22)
    # canvas.create_text(CANVAS_WIDTH / 2, CANVAS_HEIGHT * 2/3, f"Level score: {lvl_score}", anchor="center", font_size = 22)
    # canvas.create_text(CANVAS_WIDTH / 2, CANVAS_HEIGHT * 3/4, f"Total score: {score + lvl_score}", anchor="center", font_size = 28)

    print_hof(canvas, CANVAS_HEIGHT / 2 - 30, lvl, hof, time, rules)
    canvas.wait_for_click()
    return lvl_score

def get_user_choice(canvas, tubes, selection_seq, tube1, tube2, selected_color, rules, x, y):
    tube = select_tube(tubes, x, y)
    if tube != None:
        if selection_seq == 1: # if it is our 1st selection
            if try_select_tube(tube, 1, BALLS_PER_TUBE, selected_color, rules): # has to have at least one ball inside
                tube1 = tube
                ball = tube1['balls'][0]
                selected_color = ball['color']
                # select and store as selected_ball
                canvas.set_outline_color(ball['obj'], "black")
                selection_seq = 2

        else: # it is our 2nd choice
            if tube == tube1: # if user selects the same tube, we unselect it
                deselect_ball(canvas, tube1)
                tube1 = None
                selected_color = None
                selection_seq = 1
            else:
                if try_select_tube(tube, 0, BALLS_PER_TUBE - 1, selected_color, rules): # we need a tube with at least 1 free space left
                    tube2 = tube
    return (selection_seq, tube1, tube2, selected_color)

def deselect_ball(canvas, tube):
    # deselect previous ball
    ball = tube['balls'][0]
    canvas.set_outline_color(ball['obj'], "transparent")

def move_ball(tube1, tube2, canvas):
    ball = tube1['balls'].pop(0)
    last_height = tube2['pos']['y2'] - len(tube2['balls']) * SIZE
    tube2['balls'].insert(0, ball)
    canvas.moveto(ball['obj'], tube2['pos']['x1'] + TUBE_RIM, last_height + TUBE_RIM - SIZE)

def try_select_tube(tube, min_balls, max_balls, selected_color, rules):
    balls = tube['balls']
    balls_count_ok = len(balls) >= min_balls and len(balls) <= max_balls
    if not balls_count_ok:
        return False
    if selected_color == None:
        return True
    if rules == NORMAL:
        return len(balls) == 0 or balls[0]['color'] == selected_color  
    return True

def select_tube(tubes, x, y):
    for tube in tubes:
        pos = tube['pos']
        if (pos['x1'] <= x 
        and pos['x2'] >= x 
        and pos['y1'] <= y 
        and pos['y2'] >= y):
            return tube
    return None

def init_lvl(canvas, rules, lvl, MAX_LVL, score, moves):
    # set lvl between 3 and len(COLORS_AVAILABLE)
    canvas.clear()
    tubes = []
    picked_colors = get_random_colors(lvl + 2)
    balls = prepare_random_balls(BALLS_PER_TUBE, picked_colors)
    tubes_needed = lvl + 2 + 2 # on lvl 1 we start from 3 filled tubes (1 + 2) but also need 2 more empty ones
    draw_centered_tubes(canvas, tubes_needed, balls, tubes)
    level_text = canvas.create_text(10, 10, f"Level: {lvl} / {MAX_LVL}", font_size = 32)
    canvas.create_text(CANVAS_WIDTH / 2, 10, f"Rules: {rules}", anchor="n", font_size = 32)
    score_text = canvas.create_text(CANVAS_WIDTH - 10, 10, get_score_text(score), font_size = 32, anchor = "ne")
    moves_text = canvas.create_text(10, CANVAS_HEIGHT - 42, get_moves_text(moves), font_size = 32)

    x = CANVAS_WIDTH - 10
    y = CANVAS_HEIGHT - 10

    restart_lvl = canvas.create_rectangle(x - 140, y - 40, x, y, "silver")
    canvas.create_text(x - 70, y -20, "restart lvl", font_size = 24, anchor = "center")
    return (tubes, level_text, score_text, moves_text, restart_lvl)

def prepare_random_balls(count, picked_colors):
    out = []
    # we get BALLS_PER_TUBE (count) of each color from picked_colors list
    for color in picked_colors:
        for i in range(count):
            out.append(color)
    while not random_enough(out):
        random.shuffle(out)
    return out

def random_enough(balls):
    tubes_count = len(balls) // BALLS_PER_TUBE
    for tube in range(tubes_count):
        balls_slice = balls[tube * BALLS_PER_TUBE: (tube + 1) * BALLS_PER_TUBE]
        count = 0
        last_color = balls_slice[0] # remember 1st color as our "last"
        for color in balls_slice:
            if color == last_color:
                count += 1
        if count == BALLS_PER_TUBE:
            return False

    return True

def draw_centered_tubes(canvas, count, balls, tubes):
    tube_width = SIZE + 2 * TUBE_RIM
    x_start = (CANVAS_WIDTH - count * (tube_width + TUBE_PADDING )) / 2
    y_start = (CANVAS_HEIGHT - BALLS_PER_TUBE * SIZE - TUBE_RIM ) / 2
    for i in range(count):
        x = x_start + i * (tube_width + TUBE_PADDING)
        draw_tube(canvas, i, x, y_start)
    for i in range(count):
        x = x_start + i * (tube_width + TUBE_PADDING)
        balls_slice = balls[i * BALLS_PER_TUBE: (i + 1) * BALLS_PER_TUBE]
        tube = draw_balls(canvas, i, x, y_start, balls_slice)
        tubes.append(tube)

def get_random_colors(count):
    available = COLORS_AVAILABLE.copy() # clone array
    out = []
    for i in range(count):
        color = random.choice(available)
        out.append(color)
        available.remove(color)
    return out

def draw_tube(canvas, idx, x, y):
    # tube right
    x2_t = x + SIZE
    # tube bottom
    y2_t = y + SIZE * BALLS_PER_TUBE
    y2_rounded = y2_t + DR2 - SIZE // 2

    # draw rounded bottom
    canvas.create_oval(x + DR1, y2_t + DR2 - SIZE + 1, x2_t + DR2, y2_t + DR2 +1, "white", TUBE_COLOR)
    # delete top half of the circle
    canvas.create_rectangle(x + DR1 - 2, y2_t + DR2 - SIZE - 1, x2_t + DR2 + 2, y2_t + DR2 - SIZE //2, "white")
    # tube body
    canvas.create_line(x + DR1, y, x + DR1, y2_rounded, TUBE_COLOR)
    canvas.create_line(x2_t + DR2, y, x2_t + DR2, y2_rounded, TUBE_COLOR)
    # rim
    canvas.create_rectangle(x, y, x2_t + 20, y + DR1, "white", TUBE_COLOR)

def draw_balls(canvas, idx, x, y, balls):
    # tube right
    x2_t = x + SIZE
    # tube bottom
    y2_t = y + SIZE * BALLS_PER_TUBE
    y2_rounded = y2_t + DR2 - SIZE // 2

    balls_count = len(balls)
    collection = []
    if balls_count > 0:
        for i in range(balls_count):
            ball = balls[i]
            x1 = x + TUBE_RIM
            y1 = y + TUBE_RIM + i * SIZE
            x2 = x + TUBE_RIM + SIZE
            y2 = y1 + SIZE
            obj_id = canvas.create_oval(x1, y1, x2, y2, ball)
            collection.append({"color": ball, "obj": obj_id})
    return { 
        "balls": collection, 
        "idx": idx, 
        "pos": { 
            "x1": x, 
            "y1": y, 
            "x2": x2_t, 
            "y2": y2_t
        }
    }

if __name__ == '__main__':
    main()