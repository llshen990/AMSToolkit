# @author owhoyt
import abc
import os.path
import sys
import re
import ConfigParser
import uuid
import json
import traceback

APP_PATH = os.path.dirname(os.path.abspath(__file__ + "/../"))
sys.path.append(APP_PATH)

from lib.Helpers import OutputFormatHelper, Logger, Environments
from datetime import datetime
from lib.Validators import StrValidator, FileExistsValidator
from lib.Exceptions import PythonSASConnectorException, JobSuccessException
from lib.Job.Jobs import Shell


class AbstractPythonSASConnector(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, debug=False):
        self.logger = None
        self.debug = True if debug else False

        # set some defaults / setup some config data
        self.config = ConfigParser.ConfigParser()
        self.config.read(APP_PATH + '/Config/ssod_validator.cfg')

        if not self.config.has_option('DEFAULT', 'ssoaid_bin_dir'):
            raise PythonSASConnectorException('ssoaid bin directory is not defined.')

        if not self.config.has_option('DEFAULT', 'logs_dir'):
            raise PythonSASConnectorException('No logs dir defined in config.')

        self.ssoaid_bin_dir = self.config.get('DEFAULT', 'ssoaid_bin_dir')
        self.log_dir = self.config.get('DEFAULT', 'logs_dir')
        self.uuid = uuid.uuid4().hex

        self.logger = Logger(
            os.path.join(self.log_dir, str(self) + '_automation_' + datetime.now().strftime('%Y%m%d_%H%I%S') + '.log'))

        self.query = None
        self.result = None
        self.error = None
        self.libname = None
        self.table = None
        self.passthru = False
        self.authdomain = None
        self.authdomain_opts = None
        self.__is_select = False
        self.__sas_code = ''
        # self.__python_sas_connector_out_file = '/tmp/test.out'  # @todo: do in warehouse
        self.__python_sas_connector_out_file = '/tmp/python_sas_connector_' + self.uuid + '.out'  # @todo: do in warehouse
        self.__python_sas_connector_sas_file = '/tmp/python_sas_connector_' + self.uuid + '.sas'  # @todo: do in warehouse
        self.__python_sas_connector_log_file = os.path.join(self.log_dir, 'python_sas_connector_' + self.uuid + '.log')
        self.__python_sas_connector_sas_file_obj = None
        self.__run_sas_sh_scirpt = os.path.abspath(os.path.join(self.ssoaid_bin_dir, 'sasapp.sh'))
        self.job = None  # type: Shell
        self.field_map = []
        self.primary_key_field = None

        self.environments = Environments()

        self.map_fields()

    @abc.abstractmethod
    def map_fields(self):
        return

    @abc.abstractmethod
    def class_instantiation_args(self):
        return

    def load(self, id_var):
        self._validate_libname()
        self._validate_table()
        self._validate_primary_key()
        self._validate_field_map()
        id_var = self._validate_id(id_var)

        sql = """
            SELECT
              {fields}
            FROM
              {libname}.{table}
            WHERE
              {primary_key_field} = {id};
        """.format(
            fields=",".join(self.field_map),
            libname=self._escape_var(self.libname),
            table=self._escape_var(self.table),
            primary_key_field=self._escape_var(self.primary_key_field),
            id=self._escape_var(id_var)
        )

        self.exec_query(sql)
        return self._load_single_result()

    def filter_object(self, filter_dict):
        """
        This method will return a list of objects that match the desired criteria
        :param filter_dict: Dictionary with different categories: where, group, having, order
        :type filter_dict: dict
        :return: list
        :rtype: List[AbstractPythonSASConnector]
        """
        if not filter_dict:
            raise PythonSASConnectorException(self.__whoami() + ' requires filter criteria')

        if not isinstance(filter_dict, dict):
            raise PythonSASConnectorException(self.__whoami() + ' requires a dict of columns:values to filter')

        self._validate_libname()
        self._validate_table()
        self._validate_primary_key()
        self._validate_field_map()
        conditions = self._build_conditions_from_dict(filter_dict)

        sql = """
            SELECT
              {fields}
            FROM
              {libname}.{table}
            {conditions}
        """.format(
            fields=",".join(self.field_map),
            libname=self.libname,
            table=self.table,
            conditions=conditions  # do not put _escape_var on this
        )

        self.exec_query(sql)

        return self._load_all_results()

    def _build_conditions_from_dict(self, filter_dict):
        """
        Builds conditions for filtering data
        :param filter_dict: Options to filter by: where, group, having, order
        :type filter_dict: dict
        :return: SQL string filter
        :rtype: str
        """
        conditions_ret = ''
        where_cnt = 0
        if 'where_equal' in filter_dict and isinstance(filter_dict['where_equal'], dict) and len(
                filter_dict['where_equal']) > 0:
            for k, v in filter_dict['where_equal'].iteritems():
                if where_cnt:
                    conditions_ret += ' AND '
                else:
                    conditions_ret += ' WHERE '

                conditions_ret += k + '=' + self._escape_var(v)
                where_cnt += 1

        if 'where' in filter_dict and isinstance(filter_dict['where'], list) and len(filter_dict['where']) > 0:
            for v in filter_dict['where']:
                if where_cnt:
                    conditions_ret += ' AND '
                else:
                    conditions_ret += ' WHERE '

                conditions_ret += str(v)
                where_cnt += 1

        if 'group' in filter_dict and isinstance(filter_dict['group'], dict) and len(filter_dict['group']) > 0:
            group_cnt = 0
            for k, v in filter_dict['group'].iteritems():
                if group_cnt:
                    conditions_ret += ',  '
                else:
                    conditions_ret += os.linesep + 'GROUP BY '

                conditions_ret += str(k) + ' ' + self._escape_var(v)
                group_cnt += 1

        if 'having' in filter_dict and isinstance(filter_dict['having'], dict) and len(filter_dict['having']) > 0:
            having_cnt = 0
            for k, v in filter_dict['having'].iteritems():
                if having_cnt:
                    conditions_ret += ' AND '
                else:
                    conditions_ret += os.linesep + 'HAVING '

                conditions_ret += str(k) + '=' + self._escape_var(v)
                having_cnt += 1

        if 'order' in filter_dict and isinstance(filter_dict['order'], dict) and len(filter_dict['order']) > 0:
            order_cnt = 0
            for k, v in filter_dict['order'].iteritems():
                if order_cnt:
                    conditions_ret += ',  '
                else:
                    conditions_ret += os.linesep + 'ORDER BY '

                conditions_ret += str(k) + ' ' + str(v)
                order_cnt += 1

        return conditions_ret

    def save(self):
        # @todo: put in model validation rules as a abstract method
        # @todo: create method to escape an oracle column i.e. w/o the quotes
        self._validate_libname()
        self._validate_table()
        self._validate_primary_key()
        self._validate_field_map()

        sql = """
            UPDATE
                {libname}.{table}
        """.format(
            libname=self._escape_var(self.libname),
            table=self._escape_var(self.table),
        )

        first = 0
        for field in self.field_map:
            if first:
                sql += "," + os.linesep
            sql += "set " + field + "=" + self._escape_var(getattr(self, field))
            if not first:
                first += 1

        sql += os.linesep
        sql += """
            WHERE
                {primary_key_field} = {id};
        """.format(
            primary_key_field=self._escape_var(self.primary_key_field),
            id=self._escape_var(getattr(self, self.primary_key_field.lower()))
        )

        return self.exec_query(sql)

    def delete(self, id_var):
        self._validate_libname()
        self._validate_table()
        self._validate_primary_key()
        self._validate_field_map()
        id_var = self._validate_id(id_var)

        sql = """
            DELETE FROM
                {libname}.{table}
            WHERE
                {primary_key_field} = {id};
        """.format(
            libname=self._escape_var(self.libname),
            table=self._escape_var(self.table),
            primary_key_field=self._escape_var(self.primary_key_field),
            id=id_var
        )

        return self.exec_query(sql)

    def add(self, data={}):
        # @todo: change to saving the object instead
        # @todo: make data={} optional
        # @todo: put in model validation rules as a abstract method
        self._validate_libname()
        self._validate_table()
        self._validate_field_map()

        sql = """
            INSERT INTO
                {libname}.{table}
                (
        """.format(
            libname=self.libname,
            table=self.table,
        )

        if not data:
            first = 0
            for field in self.field_map:
                if first:
                    sql += "," + os.linesep
                sql += field
                if not first:
                    first += 1

            sql += os.linesep
            sql += """
                                )
                            VALUES
                                (

                        """

            first = 0
            for field in self.field_map:
                if first:
                    sql += "," + os.linesep
                sql += self._escape_var(getattr(self, field))
                if not first:
                    first += 1

            sql += os.linesep
            sql += """
                                )
                            ;
                        """
        else:
            self._validate_data_to_field_map(data)
            first = 0
            for field, value in data.iteritems():
                if first:
                    sql += "," + os.linesep
                sql += field
                if not first:
                    first += 1

            sql += os.linesep
            sql += """
                    )
                VALUES
                    (
                    
            """

            first = 0
            for field, value in data.iteritems():
                if first:
                    sql += "," + os.linesep
                sql += self._escape_var(value)
                if not first:
                    first += 1

            sql += os.linesep
            sql += """
                    )
                ;
            """

        return self.exec_query(sql)

    @staticmethod
    def _validate_id(id_var):
        id_var = str(id_var).strip()

        if not id_var:
            raise PythonSASConnectorException('ID required')

        return id_var

    def _validate_primary_key(self):
        if not self.primary_key_field:
            raise PythonSASConnectorException('Primary Key Field Required')

        str_v = StrValidator(True)
        if not str_v.validate(self.primary_key_field, {min: 1}):
            raise PythonSASConnectorException('Invalid primary_key_field')

        return True

    def _validate_data_to_field_map(self, data):
        if not data:
            raise PythonSASConnectorException('Data Required')

        if not isinstance(data, dict):
            raise PythonSASConnectorException('Data must be a dict')

        for k, v in data.iteritems():
            if k not in self.field_map:
                raise PythonSASConnectorException(
                    'Class ' + str(self) + ' does not have attribute of: ' + k + ' to add to the model')

        return True

    def _validate_field_map(self):
        if not self.field_map:
            raise PythonSASConnectorException('Field Map Required')

        if not isinstance(self.field_map, list):
            raise PythonSASConnectorException('Field Map must be a list.')

        for field in self.field_map:
            if not hasattr(self, field):
                raise PythonSASConnectorException('Class ' + str(self) + ' does not have attribute of: ' + field)

        return True

    def _escape_var(self, variable):
        # @todo: figure out a better way to deal with this as it will break for unicode and possibly other situations
        # but it is better than nothing.  Problem is SAS/Access engine does not allow you to bind variables.
        if isinstance(variable, int):
            return str(variable)
        elif self._is_number(variable):
            return variable

        return json.dumps(variable)

    def exec_query(self, sql):
        try:
            # @todo: put in debug to print out queries
            self.query = str(sql).strip()
            select_reg_ex = re.compile('^SELECT', re.IGNORECASE)
            if select_reg_ex.match(self.query):
                self.__is_select = True
            self._connect_to_sas()
        except PythonSASConnectorException:
            raise
        except Exception as e:
            if self.debug:
                print 'Query: ' + self.query
                traceback.print_exc()
            raise PythonSASConnectorException('Ran into an exception running exec_query: ' + str(e))

    def _connect_to_sas(self):
        self._validate_libname()
        self._validate_query()
        self._handle_passthru()
        self._build_sas_code()
        self._write_sas_code()
        self._run_sas_code()

    def _write_sas_code(self):
        self.__python_sas_connector_sas_file_obj = open(self.__python_sas_connector_sas_file, 'w')
        self.__python_sas_connector_sas_file_obj.write(self.__sas_code)
        self.__python_sas_connector_sas_file_obj.close()

    def _run_sas_code(self):
        # @todo: remove
        # return True
        # @todo: look into error handling of SAS code / in the log
        try:
            self.job = Shell(self.__run_sas_sh_scirpt, self.log_dir)  # @todo: do we need the signals?
            self.job.add_attribute('-sysin')
            self.job.add_attribute(self.__python_sas_connector_sas_file)
            self.job.add_attribute('-log')
            self.job.add_attribute(self.__python_sas_connector_log_file)
            self.job.signal_path_txt = os.path.basename(self.__run_sas_sh_scirpt)
            self.job.job_type = os.path.basename(self.__run_sas_sh_scirpt)
            self.job.start_job()
        except JobSuccessException:
            self.log_it('job ' + self.job.get_job_name() + ' completed successfully')
        except Exception as e:
            self.error = True
            raise PythonSASConnectorException('Encountered error when running SAS code: ' + str(e))

    def _build_sas_code(self):
        self.__sas_code = "%fcsautoexec(ECM_AUTO=1,ECM_DB=1,AML_AUTO=1,KC_DB=1);" + os.linesep
        # self.__sas_code += "libname fcs_rpt oracle authdomain='OraAuth_fcs' path=\"&_ORACLEHOST\";" + os.linesep
        self.__sas_code += self.environments.get_reporting_libname_stmt() + os.linesep
        self.__sas_code += "proc sql;" + os.linesep
        self.__sas_code += self.query + os.linesep
        self.__sas_code += "quit;" + os.linesep

        if self.__is_select:
            self.__sas_code += os.linesep + os.linesep
            self.__sas_code += "data _null_;" + os.linesep
            self.__sas_code += "   file '" + self.__python_sas_connector_out_file + "' dsd delimiter=\"|\";" + os.linesep
            self.__sas_code += "   set work.pythonSasConn;" + os.linesep
            self.__sas_code += "   put (_all_)(+0);" + os.linesep
            self.__sas_code += "run;" + os.linesep

        return True

    def _handle_passthru(self):
        if self.passthru and self.__is_select:
            self._validate_authdomain()
            tmp_query = self.query
            self.query = "connect to oracle as bu1 (authdomain=\"" + self.authdomain + "\"" + self.authdomain_opts + ");" + os.linesep
            self.query += "create table work.pythonSasConn as " + os.linesep
            self.query += "SELECT * from connection to bu1(" + os.linesep
            self.query += tmp_query + os.linesep
            self.query += ");" + os.linesep
            self.query += "disconnect from bu1;" + os.linesep
        elif self.__is_select:
            tmp_query = self.query
            self.query = "create table work.pythonSasConn as " + os.linesep
            self.query += tmp_query
            self.query += ";"

        return True

    def _load_single_result(self, override_out_file=None):
        """
        This method will load the object itself.
        :return: True upon success
        :rtype: bool
        """

        if override_out_file:
            self.__python_sas_connector_out_file = override_out_file

        fev = FileExistsValidator(True)
        if not fev.validate(self.__python_sas_connector_out_file):
            raise PythonSASConnectorException(
                'No results available to return.  Something is wrong as the following file no longer exists: ' + self.__python_sas_connector_out_file)

        with open(self.__python_sas_connector_out_file) as fp:
            try:
                for row in fp:
                    row = unicode(row, 'UTF-8').strip()
                    cols = row.split('|')

                    if len(cols) != len(self.field_map):
                        raise PythonSASConnectorException(
                            'Invalid number of columns returned - cannot load object ' + str(self))
                    for field in self.field_map:
                        setattr(self, field, str(cols.pop(0)).strip())
                    return True
            except PythonSASConnectorException:
                raise
            except Exception:
                raise

    def _load_all_results(self, override_out_file=None):
        """
        This method will return a list of objects loaded from the results of the executed SAS query.
        :return: List of loaded objects or an empty list
        :rtype: list[AbstractPythonSASConnector]
        """

        if override_out_file:
            self.__python_sas_connector_out_file = override_out_file

        fev = FileExistsValidator(True)
        if not fev.validate(self.__python_sas_connector_out_file):
            raise PythonSASConnectorException(
                'No results available to return.  Something is wrong as the following file no longer exists: ' + self.__python_sas_connector_out_file)

        ret_list = []
        with open(self.__python_sas_connector_out_file) as fp:
            try:
                for row in fp:

                    obj = self.__class__(self.class_instantiation_args)
                    row = unicode(row, 'UTF-8').strip()
                    cols = row.split('|')

                    if len(cols) != len(obj.field_map):
                        raise PythonSASConnectorException(
                            'Invalid number of columns returned - cannot load object ' + str(obj))
                    for field in obj.field_map:
                        setattr(obj, field, str(cols.pop(0)).strip())
                    ret_list.append(obj)
            except PythonSASConnectorException:
                raise
            except Exception:
                raise

        return ret_list

    def _validate_authdomain(self):
        if not self.authdomain:
            raise PythonSASConnectorException('Authdomain required')

        if not self.authdomain_opts:
            raise PythonSASConnectorException('Authdomain opts required')

        return True

    def _validate_libname(self):
        if not self.libname:
            raise PythonSASConnectorException('Libname required')

        str_v = StrValidator(True)
        if not str_v.validate(self.libname, {min: 1, max: 8}):
            raise PythonSASConnectorException('Invalid Libname')

        return True

    def _validate_table(self):
        if not self.table:
            raise PythonSASConnectorException('Table Required')

        str_v = StrValidator(True)
        if not str_v.validate(self.table, {min: 1}):
            raise PythonSASConnectorException('Invalid Table')

        return True

    def _validate_query(self):
        if not self.query:
            raise PythonSASConnectorException('Query required')

        str_v = StrValidator(True)
        if not str_v.validate(self.libname, {min: 1}):
            raise PythonSASConnectorException('Invalid Query')

        return True

    def log_it(self, message):
        """
        If debug is on, will write a message to terminal + log file.  If off, it will only write to log file.
        :param message: Message to write to log.
        :type message: str
        :return: True upon completion
        :rtype: bool
        """
        try:
            self.logger.write_debug(OutputFormatHelper.log_msg_with_time(message), self.debug)
        except Exception as e:
            raise PythonSASConnectorException(str(e))

        return True

    def dump_vars(self):
        self._validate_field_map()
        print ' ---------------- START DUMP ' + str(self) + ' ----------------'
        for field in self.field_map:
            print field + ': ' + getattr(self, field)
        print ' ---------------- END DUMP ' + str(self) + ' ------------------'

    def __whoami(self):
        import sys
        return sys._getframe(1).f_code.co_name

    @staticmethod
    def _is_number(s):
        """
        This method will return bool on if the input is a number.
        :param s: mixed
        :return: bool
        """
        try:
            float(s)
            return True
        except ValueError:
            pass

        try:
            import unicodedata
            unicodedata.numeric(s)
            return True
        except (TypeError, ValueError):
            pass
        return False

    def __str__(self):
        """magic method when you call print(self) to print the name of the class"""
        return self.__class__.__name__

    def __del__(self):
        if not self.error:
            fev = FileExistsValidator(True)
            if fev.validate(self.__python_sas_connector_out_file):
                os.remove(self.__python_sas_connector_out_file)

            if fev.validate(self.__python_sas_connector_sas_file):
                os.remove(self.__python_sas_connector_sas_file)
        pass
