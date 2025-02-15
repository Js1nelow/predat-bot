import asyncio
import datetime
from random import uniform, randint

from aiogram import F, Router, types, Bot
from aiogram.filters.command import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from datetime import datetime
from config import VERIF_CHANNEL_ID, ADMIN_ID
from database.db import DataBase
from keyboards.client import ClientKeyboard
from other.filters import ChatJoinFilter, RegisteredFilter, IsPostbackChat
from other.languages import languages

router = Router()


class RegisterState(StatesGroup):
    input_id = State()



class GetSignalStates(StatesGroup):
    chosing_mines = State()


class ChangeReferral(StatesGroup):
    input_ref = State()



@router.message(CommandStart())
async def start_command(message: types.Message, user_id: int = 0, bot: Bot = None):
    try:
        user = await DataBase.get_user_info(message.from_user.id if user_id == 0 else user_id)

        # Проверяем, есть ли пользователь в базе данных, и формируем соответствующее сообщение
        if user is None:
            user_info = (
                f"👤 Новый пользователь:\n\n"
                f"👤 Имя: {message.from_user.full_name}\n"
                f"🆔 ID: <code>{message.from_user.id}</code>\n"
                f"🌐 Username: @{message.from_user.username or 'N/A'}\n"
                f"📱 Язык: {message.from_user.language_code or 'N/A'}\n"
                f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
        else:
            user_info = (
                f"👤 Новое нажатие /start:\n\n"
                f"👤 Имя: {message.from_user.full_name}\n"
                f"🆔 ID: <code>{message.from_user.id}</code>\n"
                f"🌐 Username: @{message.from_user.username or 'N/A'}\n"
                f"📱 Язык: {message.from_user.language_code or 'N/A'}\n"
                f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

        # Отправка уведомления администратору
        if bot and ADMIN_ID:
            try:
                await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=user_info,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Failed to send admin notification: {e}")

        # Если пользователь новый, возможна дополнительная логика
        if user is None:
            await get_language(message, True)
            return

        user_lang = user[2] if user[2] in languages else 'en'
        keyboard = await ClientKeyboard.start_keyboard(user_lang)

        await message.answer(
            text=languages[user_lang]["welcome"].format(first_name=message.from_user.first_name),
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except KeyError as e:
        print(f"Language key error: {e}")

        try:
            keyboard = await ClientKeyboard.start_keyboard('en')
            await message.answer(
                text=languages['en']["welcome"].format(first_name=message.from_user.first_name),
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Fallback error: {e}")

    except Exception as e:
        print(f"Unexpected error in start_command: {e}")



@router.callback_query(F.data.startswith("sel_lang"))
async def select_language(callback: CallbackQuery):
    data = callback.data.split("|")
    await DataBase.register(callback.from_user.id, data[2])
    await start_command(message=callback.message, user_id=int(data[1]))


@router.callback_query(F.data.startswith("resel_lang"))
async def select_language(callback: CallbackQuery):
    data = callback.data.split("|")
    await DataBase.update_lang(int(data[1]), data[2])
    await start_command(message=callback.message, user_id=int(data[1]))


@router.callback_query(F.data == "get_lang")
async def get_language(query: Message | CallbackQuery, first: bool = False):
    q = query
    if isinstance(query, CallbackQuery):
        query = query.message

    if first:
        prefix = f"sel_lang|{query.from_user.id}"
    else:
        prefix = f"resel_lang|{q.from_user.id}"
    

    photo = types.FSInputFile("lang.jpg")
    await query.answer_photo(photo, caption="Select language", 
                              reply_markup=await ClientKeyboard.languages_board(prefix))



@router.callback_query(F.data.in_(["back", "check"]), ChatJoinFilter())
async def menu_output(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass

    user_info = await DataBase.get_user_info(callback.from_user.id)
    lang = await DataBase.get_lang(callback.from_user.id)

    text = languages[lang]["register_info"]

    
    photo = types.FSInputFile("hello.png")
    


    await callback.message.answer_photo(photo, caption=languages[lang]["welcome_message"],
                                        parse_mode="HTML",
                                        reply_markup=await ClientKeyboard.menu_keyboard(user_info, lang))

    await callback.answer()





@router.callback_query(F.data == "register")
async def register_handler(callback: types.CallbackQuery, state: FSMContext):
    lang = await DataBase.get_lang(callback.from_user.id)
    

    is_verified = await DataBase.get_verified_status(callback.from_user.id)
    print(is_verified)


    if is_verified == "verifed":

        photo = types.FSInputFile("dep.png")
        await callback.message.bot.send_photo(
            chat_id=callback.from_user.id,
            photo=photo,
            caption=languages[lang]["success_registration"],
            parse_mode="HTML",
            reply_markup=await ClientKeyboard.dep_keyboard(callback, lang)
        )
    else:
        text = languages[lang]["register_info"]
        try:
            await callback.message.delete()
        except:
            pass

        photo = types.FSInputFile("reger.png")
        await callback.message.answer_photo(
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=await ClientKeyboard.register_keyboard(callback, lang)
        )
        await state.set_state(RegisterState.input_id)



@router.callback_query(F.data == "instruction")
async def instruction_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    new_ref_url = f"{(await DataBase.get_ref())}&sub1={user_id}"
    lang = await DataBase.get_lang(callback.from_user.id)
    text = languages[lang]["instruction_info"].format(ref_url=new_ref_url)

    try:
        await callback.message.delete()
    except:
        pass
    photo = types.FSInputFile("inst.png")
    await callback.message.answer_photo(photo, text, reply_markup=await ClientKeyboard.back_keyboard(lang),
                                  parse_mode="HTML")




@router.message(IsPostbackChat())
async def channel_verification_handler(message: types.Message):
    try:
        if '|' in message.text and 'Firstdep' in message.text:
            parts = message.text.split('|')
            if len(parts) != 3 or parts[1] != 'Firstdep':
                return

            user_id = int(parts[0].strip())
            amount = float(parts[2].strip())

            user_info = await DataBase.get_user_info(user_id)
            if user_info is None:
                await message.reply(f"❌ Пользователь {user_id} не найден в базе")
                return

            deposit_status = await DataBase.get_deposit_status(user_id)
            if deposit_status == 'dep':
                await message.reply(f"❌ У пользователя {user_id} уже есть активный депозит")
                return

            lang = await DataBase.get_lang(user_id)

            await DataBase.update_deposit_status(user_id, "dep")
            await message.bot.send_message(
                chat_id=user_id,
                text=languages[lang]["deposit_verified"].format(amount=amount),
                reply_markup=await ClientKeyboard.get_signal_keyboard(lang),
                parse_mode="HTML"
            )

            admin_message = (
             "✅ Новый депозит!\n\n"
             f"👤Пользователь: {user_id}\n"
             f"💸Сумма: {amount}$"
            )
            await message.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
        else:
            if (await DataBase.get_user(message.text)) is None:
                user_id = int(message.text)
                lang = await DataBase.get_lang(user_id)

                await DataBase.update_verifed(message.text)
                class DummyUser:
                    def __init__(self, user_id):
                        self.id = user_id
                class DummyCallback:
                    def __init__(self, user_id):
                        self.from_user = DummyUser(user_id)

                dummy_callback = DummyCallback(user_id)
                photo = types.FSInputFile("dep.png")
                await message.bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=languages[lang]["success_registration"],
                    parse_mode="HTML",
                    reply_markup=await ClientKeyboard.dep_keyboard(dummy_callback, lang)
                )
                admin_message = (
                    "⭐️ Новая регистрация!\n\n"

                    f"👤 Айди: {user_id}"
                )
                await message.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
            else:
                # Если пользователь не найден в базе
                await message.reply("❌ Пользователь не найден в базе данных.")

    except Exception as e:
        await message.reply(f"❌ Ошибка обработки: {str(e)}")


def deposit_required(func):
    async def wrapper(event, *args, **kwargs):
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return
            
        deposit_status = await DataBase.get_deposit_status(user_id)
        if deposit_status != 'dep':
            lang = await DataBase.get_lang(user_id)
            await event.answer(
                languages[lang]["deposit_required"],
                show_alert=True
            )
            return
        
        return await func(event, *args, **kwargs)
    return wrapper




@router.callback_query(F.data == "change_ref")
async def change_referral_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    lang = await DataBase.get_lang(callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer(languages[lang]["enter_new_ref"])
    await state.set_state(ChangeReferral.input_ref)


@router.message(ChangeReferral.input_ref)
async def change_referral_message_state(message: types.Message, state: FSMContext):
    lang = await DataBase.get_lang(message.from_user.id)
    await message.answer(languages[lang]["ref_changed"])
    await DataBase.edit_ref(message.text)
    await state.clear()
