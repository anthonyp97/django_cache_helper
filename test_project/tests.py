from hashlib import sha256

from django.test import TestCase
from django.core.cache import cache

from cache_helper import settings
from cache_helper.decorators import cached
from cache_helper.interfaces import CacheHelperCacheable
from cache_helper.utils import _func_type, sanitize_key
from cache_helper.exceptions import CacheKeyCreationError


@cached(60*60)
def foo(a, b):
    return a + b


class CacheHelperTestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apple = Fruit('Apple')
        cls.cherry = Fruit('Cherry')

        cls.celery = Vegetable('Celery')

        cls.chicken = Meat(name='Chicken', grams_protein=20)
        cls.steak = Meat(name='Steak', grams_protein=26)

    @classmethod
    def tearDownClass(cls):
        pass

    def assertKeyInCache(self, key):
        sanitized_key = sanitize_key(key)
        self.assertTrue(sanitized_key in cache)


class Vegetable(object):
    def __init__(self, name):
        self.name = name

    def fun_math(self, a, b):
        return a + b

    @cached(60*60)
    def take_then_give_back(self, a):
        return a

    @cached(60*60)
    def instance_method(self):
        return self.name

    @classmethod
    def class_method(cls):
        return cls

    @classmethod
    @cached(60*60)
    def add_sweet_letter(cls, a):
        return cls.__name__ + a

    @staticmethod
    @cached(60*60)
    def static_method(a):
        return a

    @staticmethod
    @cached(60*60)
    def foo(a, b):
        return a + b


class Fruit(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'MyNameIs{0}'.format(self.name)

    @cached(60*60)
    def fun_math(self, a, b):
        return a + b

    @cached(60*60)
    def take_then_give_back(self, a):
        return a

    @property
    @cached(60*60)
    def is_green(self):
        if self.name == 'Apple':
            return True
        return False

    @classmethod
    @cached(60*60)
    def add_sweet_letter(cls, a):
        return cls.__name__ + a

    @staticmethod
    @cached(60*60)
    def static_method(a):
        return a


class Meat(CacheHelperCacheable):
    def __init__(self, name, grams_protein):
        self.name = name
        self.grams_protein = grams_protein

    def __str__(self):
        return 'MyNameIs{0}'.format(self.name)

    def get_cache_helper_key(self):
        return '{name}:{grams_protein}'.format(name=self.name, grams_protein=self.grams_protein)

    @staticmethod
    @cached(60*5)
    def get_grams_protein(meat):
        return meat.grams_protein


class FuncTypeTest(CacheHelperTestBase):
    """
    Test make sure functions catch right type
    """
    def assertFuncType(self, func, tp):
        self.assertEqual(_func_type(func), tp)

    def test_module_func(self):
        self.assertFuncType(foo, 'function')

    def test_instance_method(self):
        self.assertFuncType(self.celery.instance_method, 'method')

    def test_static_method(self):
        self.assertFuncType(Vegetable.static_method, 'function')

    def test_class_method(self):
        self.assertFuncType(Vegetable.class_method, 'class_method')


class BasicCacheTestCase(CacheHelperTestBase):
    def test_function_cache(self):
        foo(1, 2)
        expected_key = 'tests.foo;1,2;'
        self.assertKeyInCache(expected_key)


class MultipleCallsDiffParamsTestCase(CacheHelperTestBase):

    def test_two_models(self):
        # Call first time and place in cache
        apple_val = self.apple.fun_math(10, 10)
        cherry_val = self.cherry.fun_math(15, 10)

        self.assertEqual(self.apple.fun_math(10, 10), apple_val)
        self.assertEqual(self.cherry.fun_math(15, 10), cherry_val)

    def test_class_method(self):
        Fruit.add_sweet_letter('a')
        Fruit.add_sweet_letter('c')

        add_sweet_letter_a_key = 'tests.Fruit.add_sweet_letter;a;'
        add_sweet_letter_c_key = 'tests.Fruit.add_sweet_letter;c;'

        self.assertKeyInCache(add_sweet_letter_a_key)
        self.assertKeyInCache(add_sweet_letter_c_key)

        self.assertEqual(Fruit.add_sweet_letter('a'), 'Fruita')
        self.assertEqual(Fruit.add_sweet_letter('c'), 'Fruitc')


class KeyLengthTestCase(CacheHelperTestBase):

    def test_keys_are_truncated_beyond_250_chars(self):
        try:
            apple_val = self.apple.fun_math(('a' * 200), ('b' * 200))
            self.assertTrue(isinstance(apple_val, str))
        except Exception:
            self.fail('Keys are not being correctly truncated.')


class KeyCreationTestCase(CacheHelperTestBase):
    def tearDown(self):
        settings.MAX_DEPTH = 2

    def test_same_method_name_different_class(self):
        """
        Two different classes with the same method name should have different cache keys
        """
        apple_take_give_back_cherry_key = self.apple.take_then_give_back.get_cache_key(self.cherry)
        celery_take_give_back_cherry_key = self.celery.take_then_give_back.get_cache_key(self.cherry)
        self.assertNotEqual(apple_take_give_back_cherry_key, celery_take_give_back_cherry_key)

    def test_same_class_method_name_different_class(self):
        """
        Two different classes with the same class method name should have different cache keys
        """
        apple_add_sweet_cherry_key = self.apple.add_sweet_letter.get_cache_key(self.cherry)
        celery_add_sweet_cherry_key = self.celery.add_sweet_letter.get_cache_key(self.cherry)
        self.assertNotEqual(apple_add_sweet_cherry_key, celery_add_sweet_cherry_key)

    def test_same_static_method_name_different_class_instance_reference(self):
        """
        Two different classes with the same static method name should have different cache keys
        """
        apple_static_method_key = self.apple.static_method.get_cache_key(self.cherry)
        celery_static_method_key = self.celery.static_method.get_cache_key(self.cherry)
        self.assertNotEqual(apple_static_method_key, celery_static_method_key)

    def test_same_static_method_name_different_class_class_reference(self):
        """
        Two different classes with the same static method name should have different cache keys
        """
        fruit_static_method_key = Fruit.static_method.get_cache_key(self.cherry)
        vegetable_static_method_key = Vegetable.static_method.get_cache_key(self.cherry)
        self.assertNotEqual(fruit_static_method_key, vegetable_static_method_key)

    def test_same_function_name_from_module_level(self):
        vegetable_static_method_key = Vegetable.foo.get_cache_key(1, 2)
        module_level_key = foo.get_cache_key(1, 2)
        self.assertNotEqual(vegetable_static_method_key, module_level_key)

    def test_args_kwargs_properly_convert_to_string(self):
        """
        Surface level objects are serialized correctly with default settings...
        """
        self.apple.take_then_give_back(self.cherry)
        apple_take_cherry_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,MyNameIsCherry;'
        self.assertKeyInCache(apple_take_cherry_key)

    def test_dict_args_properly_convert_to_string(self):
        self.apple.take_then_give_back({1: self.cherry})
        hashed_dict_key = sha256(str(1).encode('utf-8')).hexdigest()
        expected_cache_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,,,{0},MyNameIsCherry;'.format(hashed_dict_key)
        self.assertKeyInCache(expected_cache_key)

    def test_dict_args_keep_the_same_order_when_convert_to_string(self):
        dict_arg = {1: self.cherry, 'string': 'ay carambe'}
        self.apple.take_then_give_back(dict_arg)
        expected_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,,,' \
                       '473287f8298dba7163a897908958f7c0eae733e25d2e027992ea2edc9bed2fa8,aycarambe,,' \
                       '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b,MyNameIsCherry;'
        self.assertKeyInCache(expected_key)

    def test_set_args_properly_maintain_order_and_convert_to_string(self):
        self.apple.take_then_give_back({1, 'vegetable', self.cherry})
        expected_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,,' \
                       '4715b734085d8d9c9981d91c6d5cff398c75caf44074851baa94f2de24fba4d7,' \
                       '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b,' \
                       'f8201a5264b6b89b4d92c5bc46aa2e5c3e9610e8fc9ef200df1a39c7f10e7af6;'
        self.assertKeyInCache(expected_key)

    def test_list_args_properly_convert_to_string(self):
        self.apple.take_then_give_back([self.cherry])
        expected_cache_key = 'tests.Fruit.take_then_give_back;MyNameIsApple,,MyNameIsCherry;'
        self.assertKeyInCache(expected_cache_key)

    def test_raises_depth_error(self):
        settings.MAX_DEPTH = 0
        with self.assertRaises(CacheKeyCreationError):
            self.apple.take_then_give_back([self.cherry])


class CacheableTestCase(CacheHelperTestBase):

    def test_cacheable_key_creation(self):
        Meat.get_grams_protein(self.chicken)
        grams_protein_chicken_key = 'tests.Meat.get_grams_protein;Chicken:20;'
        self.assertKeyInCache(grams_protein_chicken_key)
