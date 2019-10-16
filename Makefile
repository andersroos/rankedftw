MAKEFILE_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
BASE_DIR := $(realpath $(CURDIR)/$(MAKEFILE_DIR))
SRC_DIR := $(BASE_DIR)/src

#
# Settings
#

# Building

PIP := pip3
NPM := npm
LESSC := $(BASE_DIR)/node_modules/.bin/lessc
WEBPACK := $(BASE_DIR)/node_modules/.bin/webpack
ESLINT := $(BASE_DIR)/node_modules/.bin/eslint

DEFAULT_DB := rankedftw

PROD_JS :=

PYTHON_INCLUDE := /usr/include/python3.6
LIB_PYTHON := :libpython3.6m.so
LIB_BOOST_PYTHON := boost_python-py36

GLO_INCLUDE := $(BASE_DIR)/contrib/glo-cpplib/include

# Testing

NOSE := nosetests-3.4
NOSE_COVERAGE := coverage3 run --parallel-mode --timid /usr/bin/nosetests3

# Running

DEV_PORT := 8000

# Override

-include local.mk

#
# Build vars
#

TASKS_MANAGE = $(BASE_DIR)/tasks/manage.py
SITE_MANAGE = $(BASE_DIR)/site/manage.py

SITE_CSS = $(BASE_DIR)/site/static/site.css
SITE_JS = $(BASE_DIR)/site/static/site.js

CXXFLAGS = -fPIC -g -O2 -DDEFAULT_DB=\"$(DEFAULT_DB)\" -std=c++14 -Wall \
           -I$(SRC_DIR) -I$(PYTHON_INCLUDE) -I$(GLO_INCLUDE) -I/usr/include/postgresql

COMMON_OBJS = $(SRC_DIR)/io.o $(SRC_DIR)/db.o $(SRC_DIR)/exception.o $(SRC_DIR)/util.o

SC2_OBJS = $(SRC_DIR)/sc2.o $(SRC_DIR)/get.o $(SRC_DIR)/ranking_data.o $(SRC_DIR)/py_log.o	\
           $(SRC_DIR)/test_aid.o $(SRC_DIR)/ladder_handler.o $(COMMON_OBJS)
SC2_LIBS = -l$(LIB_BOOST_PYTHON) -lboost_system -l$(LIB_PYTHON) -lpq -lboost_serialization	\
           -lboost_iostreams -ljsoncpp

SERVER_OBJS = $(COMMON_OBJS) $(SRC_DIR)/log.o $(SRC_DIR)/server.o $(SRC_DIR)/udp_handler.o	\
	      $(SRC_DIR)/ladder_handler.o $(SRC_DIR)/tcp_handler.o
SERVER_LIBS = -l$(LIB_BOOST_PYTHON) -lboost_system -l$(LIB_PYTHON) -lboost_serialization -lboost_iostreams	\
              -lboost_system -lpq -lboost_thread -lpthread -lboost_program_options -ljsoncpp

DOIT_OBJS = $(COMMON_OBJS) $(SRC_DIR)/log.o $(SRC_DIR)/doit.o
DOIT_LIBS = -l$(LIB_BOOST_PYTHON) -lboost_system -l$(LIB_PYTHON) -lboost_serialization -lboost_iostreams -lpq

MIGRATE_OBJS = $(COMMON_OBJS) $(SRC_DIR)/log.o $(SRC_DIR)/migrate.o
MIGRATE_LIBS = -l$(LIB_BOOST_PYTHON) -lboost_system -l$(LIB_PYTHON) -lboost_serialization -lboost_iostreams -lpq

#
# Functions
#

# recursive wildcard function
# usage: $(call rwildcard,<dir ending in / or empty for curdir>,<space separated patterns>)
rwildcard = $(foreach d,$(wildcard $1*),$(call rwildcard,$d/,$2) $(filter $(subst *,%,$2),$d)) 

#
# Targets
#

.PHONY: default pep8 run test build init check js css


default: build

init-submodules:
	git submodule update --init

init-dependencies:
	$(PIP) install --upgrade -r $(BASE_DIR)/requirements.txt
	$(NPM) install

init: init-submodules init-dependencies

pep8:
	pep8 --ignore=W602,W391,W293,E701,E241,E201,E402,W503,E116 --max-line-length=120 --exclude=./main/migrations .

eslint:
	$(ESLINT) ./site/js

check: pep8 eslint	

build: lib/sc2.so lib/doit lib/server lib/migrate js css

%.o: %.cpp $(call rwildcard, $(BASE_DIR)/src/, *.hpp)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

lib/sc2.so: $(SC2_OBJS)
	$(CXX) -shared -o $@ $^ $(SC2_LIBS)

lib/server: $(SERVER_OBJS)
	$(CXX) -o $@ $^ $(SERVER_LIBS)

lib/doit: $(DOIT_OBJS)
	$(CXX) -o $@ $^ $(DOIT_LIBS)

lib/migrate: $(MIGRATE_OBJS)
	$(CXX) -o $@ $^ $(MIGRATE_LIBS)

run: build
	PROD_JS=$(PROD_JS) ./aid/tools/run.py "$(SITE_MANAGE) runserver 0.0.0.0:$(DEV_PORT)" "$(WEBPACK) --watch" "./lib/server"

run-web: build
	PROD_JS=$(PROD_JS) ./aid/tools/run.py "$(SITE_MANAGE) runserver 0.0.0.0:$(DEV_PORT)" "$(WEBPACK) --watch"

run-server: build
	./aid/tools/run.py "./lib/server"

create-migration:
	$(SITE_MANAGE) makemigrations

migrate-db:
	$(SITE_MANAGE) migrate main

migrate-list:
	@$(SITE_MANAGE) migrate main --changes
	@$(SITE_MANAGE) migrate main --list

dry-run-migrate-db:
	$(SITE_MANAGE) migrate main --db-dry-run --verbosity=2

$(SITE_CSS): $(BASE_DIR)/site/css/all.less
	$(LESSC) $< $@

css: $(SITE_CSS)

$(SITE_JS): $(call rwildcard, $(BASE_DIR)/site/js/, *.js)
	PROD_JS=$(PROD_JS) $(WEBPACK)

js: $(SITE_JS)

test:
	@if [ ! -f $(BASE_DIR)/local.py ]; then cp local.py.sample local.py; fi
	@mkdir -p $(BASE_DIR)/.build
	$(NOSE) $(BASE_DIR)/test
	$(NOSE) $(BASE_DIR)/pg_test

coverage:
	@rm -f $(BASE_DIR)/.coverage*
	@mkdir -p $(BASE_DIR)/.build
	$(NOSE_COVERAGE) $(BASE_DIR)/test
	@for f in `find $(BASE_DIR)/pg_test -name '*test.py'`; do \
		echo $(NOSE_COVERAGE) $$f; \
		$(NOSE_COVERAGE) $$f; \
	done
	coverage3 combine
	coverage3 report -m --omit=/usr*,aid*,lib*,local*,pg_test*,test*
	rm -rf coverage-code
	coverage3 html -d coverage-code --omit=/usr*,aid*,lib*,local*,pg_test*,test*
	firefox coverage-code/index.html

coverage-unit:
	@rm -f $(BASE_DIR)/.coverage*
	@mkdir -p $(BASE_DIR)/.build
	@for f in \
		$(BASE_DIR)/test/fetch_new_test.py\
		$(BASE_DIR)/test/refetch_strangeness_nyd_test.py\
	; do \
		echo $(NOSE_COVERAGE) $$f; \
		$(NOSE_COVERAGE) $$f; \
	done
	coverage3 combine
	coverage3 report -m --omit=/usr*,aid*,lib*,local*,pg_test*,test*
	rm -rf coverage-code
	coverage3 html -d coverage-code --omit=/usr*,aid*,lib*,local*,pg_test*,test*
	firefox coverage-code/index.html

clean:
	find . -name '*.pyc' -o -name '__pycache__' -o -name '*,coverage' -o -name '*~' \
		| xargs \rm -fr
	\rm -rf version .build coverage-code
	\rm -f lib/sc2.so
	\rm -f src/*.o
	\rm -f $(SITE_JS)* $(SITE_CSS)*
	\rm -fr dist/*/build

clean-test-data:
	@for i in `psql -A -t -X -c "SELECT datname FROM pg_database WHERE datname like 'test_rankedftw-%'" postgres`; do\
		echo -n "$$i "; psql -c "DROP DATABASE \"$$i\"" postgres; \
	done

todo:
	@grep -irn todo | grep -v -E -e '(\.git|Makefile)' -e .idea | grep -v -e node_modules -e site/static/site.js | sort; echo ""

# Build a docker image for running unittests.
docker-test-image: init-submodules
	mkdir -p dist/travis/build
	sudo rsync \
		--exclude-from=$(BASE_DIR)/dist/travis/exclude \
		-av \
		--delete \
		$(BASE_DIR)/ \
		$(BASE_DIR)/dist/travis/build
	docker build dist/travis -t travis

docker-test-run: 
	docker run -v /var/run/postgresql:/var/run/postgresql -it travis make test
