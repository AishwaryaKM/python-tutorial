from error2 import OperationError
from uid2 import HUGEVAL_BYTES
from objectmodel2 import we_are_translated
import os, sys

__all__ = ['ObjSpace', 'OperationError', 'Wrappable', 'W_Root']


class W_Root(object):
    """This is the abstract root class of all wrapped objects that live
    in a 'normal' object space like StdObjSpace."""
    __slots__ = ()
    _settled_ = True

    def getdict(self):
        return None

    def getdictvalue_w(self, space, attr):
        return self.getdictvalue(space, space.wrap(attr))

    def getdictvalue(self, space, w_attr):
        w_dict = self.getdict()
        if w_dict is not None:
            return space.finditem(w_dict, w_attr)
        return None

    def getdictvalue_attr_is_in_class(self, space, w_attr):
        return self.getdictvalue(space, w_attr)

    def setdictvalue(self, space, w_attr, w_value, shadows_type=True):
        w_dict = self.getdict()
        if w_dict is not None:
            space.set_str_keyed_item(w_dict, w_attr, w_value, shadows_type)
            return True
        return False

    def deldictvalue(self, space, w_name):
        w_dict = self.getdict()
        if w_dict is not None:
            try:
                space.delitem(w_dict, w_name)
                return True
            except OperationError, ex:
                if not ex.match(space, space.w_KeyError):
                    raise
        return False

    def setdict(self, space, w_dict):
        typename = space.type(self).getname(space, '?')
        raise OperationError(space.w_TypeError,
                             space.wrap("attribute '__dict__' of %s objects "
                                        "is not writable" % typename))

    # to be used directly only by space.type implementations
    def getclass(self, space):
        return space.gettypeobject(self.typedef)

    def setclass(self, space, w_subtype):
        raise OperationError(space.w_TypeError,
                             space.wrap("__class__ assignment: only for heap types"))

    def user_setup(self, space, w_subtype):
        assert False, "only for interp-level user subclasses from typedef.py"

    def getname(self, space, default):
        try:
            return space.str_w(space.getattr(self, space.wrap('__name__')))
        except OperationError, e:
            if e.match(space, space.w_TypeError) or e.match(space, space.w_AttributeError):
                return default
            raise

    def getrepr(self, space, info, moreinfo=''):
        # XXX slowish
        w_id = space.id(self)
        w_4 = space.wrap(4)
        w_0x0F = space.wrap(0x0F)
        i = 2 * HUGEVAL_BYTES
        addrstring = [' '] * i
        while True:
            n = space.int_w(space.and_(w_id, w_0x0F))
            n += ord('0')
            if n > ord('9'):
                n += (ord('a') - ord('9') - 1)
            i -= 1
            addrstring[i] = chr(n)
            if i == 0:
                break
            w_id = space.rshift(w_id, w_4)
        return space.wrap("<%s at 0x%s%s>" % (info, ''.join(addrstring),
                                              moreinfo))

    def getslotvalue(self, index):
        raise NotImplementedError

    def setslotvalue(self, index, w_val):
        raise NotImplementedError

    def descr_call_mismatch(self, space, opname, RequiredClass, args):
        if RequiredClass is None:
            classname = '?'
        else:
            classname = wrappable_class_name(RequiredClass)
        msg = "'%s' object expected, got '%s' instead" % (
            classname, self.getclass(space).getname(space, '?'))
        raise OperationError(space.w_TypeError, space.wrap(msg))

    # used by _weakref implemenation

    def getweakref(self):
        return None

    def setweakref(self, space, weakreflifeline):
        typename = space.type(self).getname(space, '?')
        raise OperationError(space.w_TypeError, space.wrap(
            "cannot create weak reference to '%s' object" % typename))

    def clear_all_weakrefs(self):
        """Call this at the beginning of interp-level __del__() methods
        in subclasses.  It ensures that weakrefs (if any) are cleared
        before the object is further destroyed.
        """
        lifeline = self.getweakref()
        if lifeline is not None:
            # Clear all weakrefs to this object before we proceed with
            # the destruction of the object.  We detach the lifeline
            # first: if the code following before_del() calls the
            # app-level, e.g. a user-defined __del__(), and this code
            # tries to use weakrefs again, it won't reuse the broken
            # (already-cleared) weakrefs from this lifeline.
            self.setweakref(lifeline.space, None)
            lifeline.clear_all_weakrefs()

    __already_enqueued_for_destruction = False

    def _enqueue_for_destruction(self, space):
        """Put the object in the destructor queue of the space.
        At a later, safe point in time, UserDelAction will use
        space.userdel() to call the object's app-level __del__ method.
        """
        # this function always resurect the object, so when
        # running on top of CPython we must manually ensure that
        # we enqueue it only once
        if not we_are_translated():
            if self.__already_enqueued_for_destruction:
                return
            self.__already_enqueued_for_destruction = True
        self.clear_all_weakrefs()
        space.user_del_action.register_dying_object(self)

    def _call_builtin_destructor(self):
        pass     # method overridden in typedef.py


class Wrappable(W_Root):
    """A subclass of Wrappable is an internal, interpreter-level class
    that can nevertheless be exposed at application-level by space.wrap()."""
    __slots__ = ()
    _settled_ = True

    def __spacebind__(self, space):
        return self

