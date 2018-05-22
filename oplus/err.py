"""
ERR
-------


"""
import os
import pandas as pd

from . import CONF


class Err:
    WARNING = 'Warning'
    FATAL = 'Fatal'
    SEVERE = 'Severe'

    CATEGORIES = (WARNING, FATAL, SEVERE)

    def __init__(self, path, encoding=None):
        assert os.path.isfile(path), "No file at given path: '%s'." % path
        self.path = path
        self.encoding = CONF.encoding if encoding is None else encoding

        self.df = None  # multi-index dataframe
        self.info = {}
        self._parse()

        self.simulation_step_list = list(set(self.df.columns.levels[0]))

    @property
    def content(self):
        with open(self.path, encoding=self.encoding) as f:
            return f.read()

    def _parse(self):
        # todo: Manage information with ahead '*************'
        # todo: Manage 'error flag' :
        # todo:  it corresponds to error type for each error_category lines_s.split('=')[0] --> MultiIndex

        # first step: warmup
        simulation_step = 'Warmup'
        max_nb = int(1e4)
        step_df = pd.DataFrame(columns=self.CATEGORIES, index=range(0, max_nb))
        category, index_nb = None, None
        with open(self.path, encoding=self.encoding) as f:
            for row_nb, content in enumerate(f):
                # line_nb = var[0]
                line_s = content.rstrip('\n')

                # GET GENERIC INFORMATION
                if 'Program Version,EnergyPlus' in line_s:
                    self.info['EnergyPlus Simulation Version'] = str(line_s.split(',')[2].rstrip('Version '))
                    self.info['Idd_Version'] = str(line_s.split('Idd_Version ')[1])
                elif 'EnergyPlus Warmup Error Summary' in line_s:
                    self.info['EnergyPlus Warmup Error Summary'] = str(line_s.split('. ')[1])
                elif 'EnergyPlus Sizing Error Summary' in line_s:
                    self.info['EnergyPlus Sizing Error Summary'] = str(line_s.split('. ')[1])
                elif 'EnergyPlus Completed Successfully' in line_s:
                    self.info['EnergyPlus Completed Successfully'] = str(line_s.split('--')[1])

                # PARSE AND ..
                elif '************* Beginning' in line_s:
                    # SET OUTPUT DATAFRAME
                    if self.df is None:
                        iterables = [(simulation_step,), step_df.columns]
                        columns = pd.MultiIndex.from_product(iterables)
                        self.df = pd.DataFrame(index=range(0, max_nb), columns=columns)
                        self.df[simulation_step] = step_df
                    else:
                        iterables = [(simulation_step,), list(step_df.columns)]
                        columns = pd.MultiIndex.from_product(iterables)
                        multi_step_df = pd.DataFrame(index=range(0, max_nb), columns=columns)
                        multi_step_df[simulation_step] = step_df
                        self.df = self.df.join(multi_step_df)

                    # start new simulation step
                    simulation_step = line_s.split('Beginning ')[1]
                    step_df = pd.DataFrame(columns=self.CATEGORIES, index=range(0, max_nb))
                elif '** Warning **' in line_s:
                    category = 'Warning'
                    # new line (index) until next
                    series = step_df[category].dropna()
                    if len(series.index) == 0:
                        index_nb = 0
                    else:
                        index_nb = series.index[-1] + 1
                    step_df[category].loc[index_nb] = str(line_s.split('** Warning **')[1])
                elif '**  Fatal  **' in line_s:
                    category = 'Fatal'
                    series = step_df[category].dropna()
                    if len(series.index) == 0:
                        index_nb = 0
                    else:
                        index_nb = series.index[-1] + 1
                    # new line (index) until next
                    step_df[category].loc[index_nb] = str(line_s.split('**  Fatal  **')[1])
                elif '** Severe  **' in line_s:
                    category = 'Severe'
                    series = step_df[category].dropna()
                    if len(series.index) == 0:
                        index_nb = 0
                    else:
                        index_nb = series.index[-1] + 1
                    # new line (index) until next
                    step_df[category].loc[index_nb] = str(line_s.split('** Severe  **')[1])

                elif '**   ~~~   **' in line_s:  # if we are here, we are sure category and index_nb have been defined
                    # information to add to error
                    step_df[category].loc[index_nb] += '\n' + str(line_s.split('**   ~~~   **')[1])

            # save step_df
            iterables = [[simulation_step], step_df.columns]
            columns = pd.MultiIndex.from_product(iterables)
            multi_step_df = pd.DataFrame(index=range(0, max_nb), columns=columns)
            multi_step_df[simulation_step] = step_df
            if self.df is not None:  # can happen if never encounters "******* Beginning"
                self.df = self.df.join(multi_step_df)
            else:
                self.df = multi_step_df

            self.info = pd.Series(self.info, index=self.info.keys())

    def get(self, simulation_step=None, error_category=None):
        """
        Return error report dataframe.

        If not argument are given --> return raw report
        If only on argument is specify --> return swap dataframe report

        Parameters
        ----------
        simulation_step, multicolumns report dataframe level 0
        error_cat, multicolumns report dataframe level 1

        Returns
        -------
        Specify Dataframe
        """
        if simulation_step is None and error_category is None:
            return self.df.dropna(axis='rows', how='all')

        if simulation_step is not None:
            assert simulation_step in self.simulation_step_list,  \
                "The simulation_step '%s' is not referred in the error file." % simulation_step

            if error_category is not None:
                assert error_category in self.CATEGORIES, "The error_cat '%s' is wrong." % error_category
                iterables = [simulation_step, error_category]
                columns = pd.MultiIndex.from_product(iterables)
                series = self.df[simulation_step][error_category].dropna(axis='rows', how='all')

                df = pd.DataFrame(index=series.index, columns=columns)
                df[simulation_step] = series
                return df

            return self.df[simulation_step].dropna(axis='rows', how='all')

        if error_category is not None:
            assert error_category in self.CATEGORIES, "The error_category '%s' is wrong." % error_category
            df = self.df.copy()
            df.columns = df.columns.swaplevel(0, 1)
            return df[error_category].dropna(axis='rows', how='all')
