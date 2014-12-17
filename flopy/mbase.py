import numpy as np
import sys
import os
import subprocess as sp
import webbrowser as wb
import warnings

# Global variables
iconst = 1 # Multiplier for individual array elements in integer and real arrays read by MODFLOW's U2DREL, U1DREL and U2DINT.
iprn = -1 # Printout flag. If >= 0 then array values read are printed in listing file.

class BaseModel(object):
    """
    MODFLOW based models base class
    """

    def __init__(self, modelname = 'modflowtest', namefile_ext = 'nam',
                 exe_name = 'mf2k.exe', model_ws = None):
        self.__name = modelname
        self.namefile_ext = namefile_ext
        self.namefile = self.__name + '.' + self.namefile_ext
        self.packagelist = []
        self.heading = ''
        self.exe_name = exe_name
        self.external_extension = 'ref'
        if model_ws is None: model_ws = os.getcwd()
        if not os.path.exists(model_ws):
            try:
                os.makedirs(model_ws)
            except:
                #print '\n%s not valid, workspace-folder was changed to %s\n' % (model_ws, os.getcwd())
                print '\n{0:s} not valid, workspace-folder was changed to {1:s}\n'.format(model_ws, os.getcwd())
                model_ws = os.getcwd()
        self.model_ws= model_ws
        self.cl_params = ''
    
    def set_exename(self, exe_name):
        self.exe_name = exe_name
        return
        
    def add_package(self, p):
        """
        Add a flopy package object to this model.
        """
        for pp in (self.packagelist):
            if pp.allowDuplicates:
                continue
            elif (isinstance(p, type(pp))):
                print '****Warning -- two packages of the same type: ',type(p),type(pp)                 
                print 'replacing existing Package...'                
                pp = p
                return        
        self.packagelist.append( p )       
    
    def remove_package(self, pname):
        """
        Remove a package from this model.
        """
        for i,pp in enumerate(self.packagelist):  
            if pname in pp.name:               
                print 'removing Package: ',pp.name
                self.packagelist.pop(i)
                return
        raise StopIteration , 'Package name '+pname+' not found in Package list'                
            
    def build_array_name(self,num,prefix):
       return self.external_path+prefix+'_'+str(num)+'.'+self.external_extension
       
    def assign_external(self,num,prefix):           
        fname = self.build_array_name(num,prefix)
        unit = (self.next_ext_unit())
        self.external_fnames.append(fname)
        self.external_units.append(unit)       
        self.external_binflag.append(False)        
        return fname,unit
    
    def add_external(self, fname, unit, binflag=False):
        """
        Supports SWR usage and non-loaded existing external arrays
        """
        self.external_fnames.append(fname)
        self.external_units.append(unit)        
        self.external_binflag.append(binflag)
        return
    
    def remove_external(self,fname=None,unit=None):                    
        if fname is not None:
            for i,e in enumerate(self.external_fnames):
                if fname in e:
                    self.external_fnames.pop(i)
                    self.external_units.pop(i)
                    self.external_binflag.pop(i)
        elif unit is not None:
            for i,u in enumerate(self.external_units):
                if u == unit:
                    self.external_fnames.pop(i)
                    self.external_units.pop(i)
                    self.external_binflag.pop(i)
        else:
            raise Exception,' either fname or unit must be passed to remove_external()'
        return            

    def get_name_file_entries(self):
        s = ''        
        for p in self.packagelist:
            for i in range(len(p.name)):
                #s = s + ('%s %3i %s %s\n' % (p.name[i], p.unit_number[i],
                #                             p.file_name[i],p.extra[i]))
                s = s + ('{0:s} {1:3d} {2:s} {3:s}\n'.format(p.name[i], p.unit_number[i],
                                             p.file_name[i],p.extra[i]))
        return s
                
    def get_package(self, name):
        for pp in (self.packagelist):
            if (pp.name[0].upper() == name.upper()):
                return pp
        return None
   
    def get_package_list(self):
        val = []
        for pp in (self.packagelist):
            val.append(pp.name[0].upper())
        return val
    
    def change_model_ws(self,new_pth=None):
        if new_pth is None: 
            new_pth = os.getcwd()
        if not os.path.exists(new_pth):
            try:
                os.makedirs(new_pth)
            except:
                #print '\n%s not valid, workspace-folder was changed to %s\n' % (new_pth, os.getcwd())
                print '\n{0:s} not valid, workspace-folder was changed to {1:s}\n'.format(new_pth, os.getcwd())
                new_pth = os.getcwd()
        #--reset the model workspace
        self.model_ws = new_pth
        #--reset the paths for each package
        for pp in (self.packagelist):
            pp.fn_path = os.path.join(self.model_ws,pp.file_name[0])
        return None
    
    def run_model(self, pause=True, report=None):
        """
        Run the model.  This method will create and run a Windows batch file.

        Parameters
        ----------
        pause : boolean, optional
            Add a pause to the end of the batch file.
            (the default is False)
        report : string, optional
            Name of file to store stdout. (default is None).
        """
        batch_file_name = os.path.join(self.model_ws, 'run.bat')
        #error_message = ('Model executable %s not found!' % self.exe_name)
        error_message = 'Model executable {0:s} not found!'.format(self.exe_name)
        assert os.path.exists(self.exe_name), error_message

        error_message = ('Name file %s not found!' % self.namefile)
        fn_path = os.path.join(self.model_ws, self.namefile)
        assert os.path.exists(fn_path), error_message

        # Create a batch file to call code so that window remains open in case of error messages
        f = open(batch_file_name, 'w')
        #f.write('@ECHO Calling %s with %s\n' % (self.exe_name, self.namefile))
        f.write('@ECHO Calling {0:s} with {1:s}\n'.format(self.exe_name, self.namefile))
        #f.write('%s %s %s\n' % (self.exe_name, self.namefile, self.cl_params))
        f.write('{0:s} {1:s} {2:s}\n'.format(self.exe_name, self.namefile, self.cl_params))
        if (pause):
           f.write('@PAUSE\n')
        f.close()
        os.path.abspath = self.model_ws
        sp.call(batch_file_name, cwd=self.model_ws, stdout = report)
        os.remove(batch_file_name)
        return
    
    def run_model2(self, silent=True, pause=False, report=False):
        """
        This method will run the model using subprocess.Popen.

        Parameters
        ----------
        silent : boolean
            Echo run information to screen (default is True).
        pause : boolean, optional
            Pause upon completion (the default is False).
        report : string, optional
            Name of file to store stdout. (default is None).

        Returns
        -------
        (success, buff)
        success : boolean
        buff : list of lines of stdout

        """
        success = False
        buff = []
        proc = sp.Popen([self.exe_name,self.namefile], 
                        stdout=sp.PIPE, cwd=self.model_ws)
        while True:
          line = proc.stdout.readline()
          if line != '':
            if 'normal termination of simulation' in line.lower():
                success = True
            #c = line.split('\r')
            c = line.rstrip('\r\n')
            if not silent:
                #print c[0]
                print c
            if report == True:
                buff.append( c[0] )
          else:
            break
        if pause == True:
            raw_input('Press Enter to continue...')
        return ( [success,buff] )
        
    def run_model3(self):
        """
        Minimal form of run model.  No input parameters and no return
        parameters.  Runs model using subprocess.Popen.
        """
        import subprocess
        a = subprocess.Popen([self.exe_name,self.namefile], 
                             stdout=subprocess.PIPE, cwd=self.model_ws)
        b = a.communicate()
        c = b[0].split('\r')
        for cc in c:
            print cc
        
    def write_input(self, SelPackList=False):
        if self.verbose:
            print self # Same as calling self.__repr__()
            print 'Writing packages:'
        if SelPackList == False:
            for p in self.packagelist:            
                p.write_file()
                if self.verbose:
                    print p.__repr__()        
        else:
#            for i,p in enumerate(self.packagelist):  
#                for pon in SelPackList:
            for pon in SelPackList:
                for i,p in enumerate(self.packagelist):  
                    if pon in p.name:               
                        print 'writing Package: ',p.name
                        p.write_file()
                        if self.verbose:
                            print p.__repr__()        
                        break
        #--write name file
        self.write_name_file()
    
    def write_name_file(self):
        '''Every Package needs its own writenamefile function'''
        raise Exception, 'IMPLEMENTATION ERROR: writenamefile must be overloaded'

    def get_name(self):
        return self.__name

    def set_name(self, value):
        self.__name = value
        self.namefile = self.__name + '.' + self.namefile_ext
        for p in self.packagelist:
            for i in range(len(p.extension)):
                p.file_name[i] = self.__name + '.' + p.extension[i]
    name = property(get_name, set_name)

class Package(object):
    '''
    General Package class
      allowDuplicates allows more than one package of the same class to be added.
      This is needed for mfaddoutsidefile if used for more than one file.
    '''
    def __init__(self, parent, extension='glo', name='GLOBAL', unit_number=1, extra='', 
                 allowDuplicates=False):
        self.parent = parent # To be able to access the parent modflow object's attributes
        if (not isinstance(extension, list)):
            extension = [extension]
        self.extension = []
        self.file_name = []
        for e in extension:
            self.extension = self.extension + [e]
            self.file_name = self.file_name + [self.parent.name + '.' + e]
            self.fn_path = os.path.join(self.parent.model_ws,self.file_name[0])
        if (not isinstance(name, list)):
            name = [name]
        self.name = name
        if (not isinstance(unit_number, list)):
            unit_number = [unit_number]
        self.unit_number = unit_number
        if (not isinstance(extra, list)):
            self.extra = len(self.unit_number) * [extra]
        else:
            self.extra = extra
        self.url = 'index.html'
        self.allowDuplicates = allowDuplicates

        self.acceptable_dtypes = [int,np.float32,str]

    def __repr__( self ):
        s = self.__doc__
        exclude_attributes = ['extension', 'heading', 'name', 'parent', 'url']
        for attr, value in sorted(self.__dict__.iteritems()):
            if not (attr in exclude_attributes):
                if (isinstance(value, list)):
                    if (len(value) == 1):
                        #s = s + ' %s = %s (list)\n' % (attr, str(value[0]))
                        s = s + ' {0:s} = {1:s}\n'.format(attr,str(value[0]))
                    else:
                        #s = s + ' %s (list, items = %d)\n' % (attr, len(value))
                        s = s + ' {0:s} (list, items = {1:d}\n'.format(attr,len(value))
                elif (isinstance(value, np.ndarray)):
                    #s = s + ' %s (array, shape = %s)\n' % (attr, value.shape.__str__()[1:-1] )
                    s = s + ' {0:s} (array, shape = {1:s}\n'.fomrat(attr,value.shape__str__()[1:-1])
                else:
                    #s = s + ' %s = %s (%s)\n' % (attr, str(value), str(type(value))[7:-2])
                    s = s + ' {0:s} = {1:s} ({2:s}\n'.format(attr,str(value),str(type(value))[7:-2])
        return s

    def __getitem__(self, item):
        if not isinstance(item,list) and not isinstance(item,tuple):
            assert item in self.stress_period_data.data.keys(),"package.__getitem__() kper "+str(item)+" not in data.keys()"
            return self.stress_period_data[item]

        if item[1] not in self.dtype.names:
            raise Exception ("package.__getitem(): item \'"+item+"\' not in dtype names "+str(self.dtype.names))
        assert item[0] in self.stress_period_data.data.keys(),"package.__getitem__() kper "+str(item[0])+" not in data.keys()"
        if self.stress_period_data.vtype[item[0]] == np.recarray:
            return self.stress_period_data[item[0]][item[1]]

    def __setitem__(self, key, value):
        raise NotImplementedError("package.__setitem__() not implemented")

    def add_field_to_dtype(self,field_name,field_type):
        assert field_type in self.acceptable_dtypes,"mbase.package.add_field_to_dtype() field_type "+\
                                                    str(type(field_type))+" not a supported type:" +\
                                                    str(self.acceptable_dtypes)
        newdtype = [self.dtype.descr]
        tempdtype = np.dtype([(field_name,field_type)])
        newdtype.append((field_name,field_type))
        newdtypetemp = sum((dtype.descr for dtype in [self.dtype,tempdtype]), [])
        self.dtype = np.dtype(newdtypetemp)
        raise NotImplementedError("this function needs to check where any data has been set because it probably doesn't conform")


    def assign_layer_row_column_data(self, layer_row_column_data, ncols, zerobase=True):
        if (layer_row_column_data is not None):
            new_layer_row_column_data = []
            mxact = 0
            for a in layer_row_column_data:
                a = np.atleast_2d(a)                
                nr, nc = a.shape                
                assert nc == ncols, 'layer_row_column_Q must have {0:1d} columns'.format(ncols)+'\nentry: '+str(a.shape)                
                mxact = max(mxact, nr)
                if zerobase:
                    new_layer_row_column_data.append(a)
                else:
                    warnings.warn('Deprecation Warning: One-based indexing will be deprecated in future FloPy versions. Use Zero-based indexing')
                    #print 'Deprecation Warning: One-based indexing will be deprecated in future FloPy versions. Use Zero-based indexing'
                    a[:,:3] -= 1  # one-base input data, subtract 1 from layers, rows, columns
                    new_layer_row_column_data.append(a)
            return mxact, new_layer_row_column_data
        return

    def webdoc(self):
        if self.parent.version == 'mf2k':
            wb.open('http://water.usgs.gov/nrp/gwsoftware/modflow2000/Guide/' + self.url)
        elif self.parent.version == 'mf2005':
            wb.open('http://water.usgs.gov/nrp/gwsoftware/modflow2005/Guide/' + self.url)
        elif self.parent.version == 'ModflowNwt':
            wb.open('http://water.usgs.gov/nrp/gwsoftware/modflow_nwt/Guide/' + self.url)

    def write_file(self):
        '''Every Package needs its own write_file function'''
        print 'IMPLEMENTATION ERROR: write_file must be overloaded'


    def write_layer_row_column_data(self, f, layer_row_column_data):
        for n in xrange(self.parent.get_package('DIS').nper):
            if n < len(layer_row_column_data):
                a = layer_row_column_data[n]
                itmp = a.shape[0]
                #f.write('%10i%10i\n' % (itmp, self.np))
                f.write(' {0:9d} {1:9d}       STRESS PERIOD {2:6d}\n'.format(itmp, self.np, n+1))
                for b in a:
                    #f.write('%9i %9i %9i' % (b[0], b[1], b[2]) )
                    f.write(' {0:9.0f} {1:9.0f} {2:9.0f}'.format(b[0]+1, b[1]+1, b[2]+1))  # write out layer+1, row+1, col+1
                    for c in b[3:]:
                        #f.write(' %13.6e' % c)
                        f.write(' {:12.6g}'.format(c))
                    f.write('\n')
            else:
                itmp = -1
                #f.write('%10i%10i\n' % (itmp, self.np))
                f.write(' {0:9d} {1:9d}\n'.format(itmp,self.np))
    def load(self):
        """
        The load method has not been implemented for this package.

        """
        print 'This package needs a load method()'
