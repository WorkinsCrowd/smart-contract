from boa.interop.Neo.Runtime import CheckWitness, Log
from boa.interop.Neo.Storage import GetContext, Put, Delete, Get
from boa.builtins import concat, sha256, list, has_key


def get_new_game_id():
    context = GetContext()
    game_id = Get(context, 'new_game_id')
    if not game_id:
        game_id = 0
    game_id += 1
    Put(context, 'new_game_id', game_id)
    return int_to_str(game_id)


def int_to_str(num):
    if num == 0:
        return '0'
    digits = []
    while num > 0:
        digits.append(num % 10)
        num /= 10
    digits.reverse()
    result = ''
    for digit in digits:
        result = concat(result, digit + 48)
    return result


def get_answer_code(answer):
    if answer == 'rock':
        return 1
    elif answer == 'scissors':
        return 2
    elif answer == 'paper':
        return 3
    return -1


def start_play(player1, player2, answer_hash):
    context = GetContext()
    if not CheckWitness(player1):
        Log('Not authorized')
        return 0
    players_key = concat(concat(player1, '.'), player2)
    players_reverse_key = concat(concat(player2, '.'), player1)
    game_id = Get(context, players_key)
    if game_id:
        game_key_prefix = concat('game.', game_id)
        player2_key = concat(game_key_prefix, '.player2')
        answer_hash2_key = concat(game_key_prefix, '.answer_hash2')
        player2 = Get(context, player2_key)
        answer_hash2 = Get(context, answer_hash2_key)
        if answer_hash2 or player2 != player1:
            return 0
        Put(context, answer_hash2_key, answer_hash)
    else:
        game_id = get_new_game_id()
        game_key_prefix = concat('game.', game_id)
        player1_key = concat(game_key_prefix, '.player1')
        player2_key = concat(game_key_prefix, '.player2')
        answer_hash1_key = concat(game_key_prefix, '.answer_hash1')
        answer_hash2_key = concat(game_key_prefix, '.answer_hash2')
        Put(context, player1_key, player1)
        Put(context, player2_key, player2)
        Put(context, answer_hash1_key, answer_hash)
        Put(context, answer_hash2_key, 0)
        Put(context, players_key, game_id)
        Put(context, players_reverse_key, game_id)
    return game_id


def put_answer(player, game_id, value, salt, player_index):
    context = GetContext()
    game_key_prefix = concat('game.', game_id)
    player_key = concat(game_key_prefix, concat('.player', player_index))
    answer_key = concat(game_key_prefix, concat('.answer', player_index))
    answer_hash_key = concat(game_key_prefix, concat('.answer_hash', player_index))
    player1 = Get(context, player_key)
    if player1 == player:
        stored_answer = Get(context, answer_key)
        if stored_answer:
            return stored_answer
        answer_hash = sha256(concat(value, salt))
        stored_answer_hash = Get(context, answer_hash_key)
        if answer_hash == stored_answer_hash:
            new_answer = get_answer_code(value)
        else:
            new_answer = -1
        Put(context, answer_key, new_answer)
        check_winner(game_id)
        return new_answer
    return 0


def answer(player, game_id, value, salt):
    if not CheckWitness(player):
        Log('Not authorized')
        return 0
    result = put_answer(player, game_id, value, salt, '1')
    if result == 0:
        result = put_answer(player, game_id, value, salt, '2')
    return result


def resolve_rsp_winner_shortest_way(answer1, answer2):
    return (3 + answer2 - answer1) % 3


def get_winner_index(answer1, answer2):
    if answer1 == -1:
        if answer2 == -1:
            return 0
        return 2
    if answer2 == -1:
        return 1
    return resolve_rsp_winner_shortest_way(answer1, answer2)


def check_winner(game_id):
    context = GetContext()
    game_key_prefix = concat('game.', game_id)
    winner_key = concat(game_key_prefix, '.winner')
    winner = Get(context, winner_key)
    if winner:
        return winner
    answer1_key = concat(game_key_prefix, '.answer1')
    answer1 = Get(context, answer1_key)
    if not answer1:
        return -1
    answer2_key = concat(game_key_prefix, '.answer2')
    answer2 = Get(context, answer2_key)
    if not answer2:
        return -1
    player_index = get_winner_index(answer1, answer2)
    if player_index == 0:
        winner = 0
    else:
        player_key = concat('.player', int_to_str(player_index))
        winner = Get(context, concat(game_key_prefix, player_key))
    Put(context, winner_key, winner)
    delete_game(game_id)
    return winner


def delete_game(game_id):
    context = GetContext()
    game_key_prefix = concat('game.', game_id)
    player1 = Get(game_key_prefix, '.player1')
    player2 = Get(game_key_prefix, '.player2')
    players_key = concat(concat(player1, '.'), player2)
    players_reverse_key = concat(concat(player2, '.'), player1)
    Delete(context, players_key)
    Delete(context, players_reverse_key)


def Main(operation, args):
    # ''.join(['{:02x}'.format(x) for x in reversed(sha256(b'rock').digest())])

    if operation == 'StartPlay':
        game_id = start_play(args[0], args[1], args[2])
        if game_id > 0:
            Log(concat('Successful start play invoke. Game id = ', game_id))
        else:
            Log('Start play failed.')
        return game_id
    elif operation == 'Answer':
        return answer(args[0], args[1], args[2], args[3])
    else:
        Log('Method not implemented')
