# -*- coding: utf-8 -*-
#############################################################################
#
#    By KariSims (<https://karisims.github.io>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'Basic Sale Stock Restrict',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Module helps to restrict out of stock products',
    'description': """This module helps manage out-of-stock products based on 
    on-hand or forecast quantity.""",
    'author': 'KariSims',
    'website': 'https://karisims.github.io',
    'depends': ['base', 'sale_management', 'stock', 'account'],
    'data': [
        # 'views/res_config_settings_views.xml',
        # 'views/sale_order.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
