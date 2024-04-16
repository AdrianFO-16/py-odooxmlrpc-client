import xmlrpc.client
import ssl
import abc as ABC
from functools import wraps


class ClientOdooXMLRPC(ABC.ABC):
    def __init__(self, dbname, username, password, url, **kwargs):
        ssl._create_default_https_context = ssl._create_unverified_context
        self.dbname = dbname
        self.username = username
        self.password = password
        self.url = url
        self.uid = None
        self.env = None

        self.verbose = kwargs.get('verbose', False)
        self.__init_connection()

    @staticmethod
    def client(**kwargs):
        if 'model' in kwargs:
            return ClientOdooXMLRPCModel(**kwargs)
        else:
            return ClientOdooXMLRPCBase(**kwargs)
    
    @staticmethod
    def __fault_handler(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except xmlrpc.client.Fault as e:
                raise ConnectionError(e.faultString)
        return wrapper

    @__fault_handler
    def __init_connection(self):
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.url))
        self.uid = common.authenticate(self.dbname, self.username, self.password, {})
        if not self.uid:
            raise ConnectionError("Connection not sucessfull")
        self.env = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url))

    @ABC.abstractmethod
    def _implemented_behaviour(self, func, *args, **kwargs):
        return func(self, *args, **kwargs)
    
    def __env_query(func):
        def wrapper(self, *args, **kwargs):
            @wraps(func)
            @self.__fault_handler
            def inner_wrapper(self, *args, **kwargs):
                return self._implemented_behaviour(func, *args, **kwargs)
            return inner_wrapper(self, *args, **kwargs)
        return wrapper
        
    @__env_query
    def search(self, model, domain, **kwargs):
        return self.env.execute_kw(self.dbname, self.uid, self.password, model, 'search', [domain], kwargs)
    
    @__env_query
    def read(self, model, ids, fields, **kwargs):
        return self.env.execute_kw(self.dbname, self.uid, self.password, model, 'read', [ids], {'fields': fields} | kwargs)
     
    @__env_query
    def search_read(self, model, domain, fields, **kwargs):
        return self.env.execute_kw(self.dbname, self.uid, self.password, model, 'search_read', [domain], {'fields': fields} | kwargs)
    
    @__env_query
    def create(self, model, values, **kwargs):
        return self.env.execute_kw(self.dbname, self.uid, self.password, model, 'create', [values], kwargs)
    
    @__env_query
    def write(self, model, ids, values, **kwargs):
        return self.env.execute_kw(self.dbname, self.uid, self.password, model, 'write', [ids, values], kwargs)


class ClientOdooXMLRPCBase(ClientOdooXMLRPC):
    def __init__(self, dbname, username, password, url, **kwargs):
        super().__init__(dbname, username, password, url,**kwargs)

    def _implemented_behaviour(self, func, *args, **kwargs):
        return super()._implemented_behaviour(func, *args, **kwargs)


class ClientOdooXMLRPCModel(ClientOdooXMLRPC):
    
    def __init__(self, dbname, username, password, url, model, **kwargs):
        super().__init__(dbname, username, password, url, **kwargs)
        self.model = model
        
    def _implemented_behaviour(self, func, *args, **kwargs):
        try:
            return func(self, self.model, *args, **kwargs)
        except TypeError as e:
            raise TypeError(f"Model redefinition in method call not allowed, '{self.model}' and '{kwargs.get('model') or args[0]}', ommit positional argument model")
