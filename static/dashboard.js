// static/js/dashboard.js

function dashboardApp() {
    return {
        goals: [],
        isLoading: true,
        isSubmitting: false,
        
        // Filters
        searchQuery: '',
        currentDateFilter: null,
        selectedCategory: '',
        sortBy: 'date_asc', // Default sort
        listTitle: 'All Tasks',
        
        // Form Data
        newGoalTitle: '',
        newGoalDate: '',
        newGoalFreq: 'none',
        newGoalDescription: '', 
        newGoalCategory: '',

        calendar: null,

        // State for Navigation
        viewMode: 'calendar', 
        currentDate: new Date(), 
        currentMonth: new Date().getMonth(),
        currentYear: new Date().getFullYear(),
        realTodayYear: new Date().getFullYear(),
        monthNames: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],

        selectedGoal: null,
        activeTab: 'details',

        categories: [],
        showCategoryModal: false,
        newCategoryName: '',

        chatMessages: [],
        chatInput: '',
        isChatting: false,

        initDashboard() {
            this.fetchGoals();
            this.initCalendar();
            this.fetchCategories();
        },

        openModal(goal) {
            this.selectedGoal = JSON.parse(JSON.stringify(goal)); 
            this.activeTab = 'details';
            this.chatMessages = []; 
            this.chatInput = '';
            document.body.style.overflow = 'hidden'; 
        },

        closeModal() {
            this.selectedGoal = null;
            document.body.style.overflow = 'auto'; 
        },

        // --- FETCHING ---
        async fetchGoals() {
            this.isLoading = true;
            let url = `/api/goals?q=${this.searchQuery}&sort_by=${this.sortBy}&category_id=${this.selectedCategory}`;
            if (this.currentDateFilter) {
                url += `&date=${this.currentDateFilter}`;
            }

            try {
                const response = await fetch(url);
                this.goals = await response.json();
            } catch (error) {
                console.error("Error fetching goals:", error);
            } finally {
                this.isLoading = false;
            }
        },

        // --- ACTIONS ---
        async createGoal() {
            if (!this.newGoalTitle) return;
            this.isSubmitting = true;

            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            try {
                const response = await fetch('/api/goals/create', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        title: this.newGoalTitle,
                        deadline: this.newGoalDate,
                        description: this.newGoalDescription,
                        category_id: this.newGoalCategory,
                        frequency: this.newGoalFreq
                    })
                });

                if (response.ok) {
                    this.newGoalTitle = '';
                    this.newGoalDescription = '';
                    await this.fetchGoals();
                    this.calendar.refetchEvents();
                }
            } catch (error) {
                console.error("Error adding goal:", error);
            } finally {
                this.isSubmitting = false;
            }
        },

        async fetchCategories() {
            try {
                const response = await fetch('/api/categories');
                this.categories = await response.json();
                if (this.categories.length > 0) {
                    const general = this.categories.find(c => c.name === 'General');
                    if (general) {
                        this.newGoalCategory = general.id;
                    } else {
                        this.newGoalCategory = this.categories[0].id;
                    }
                }
            } catch (error) {
                console.error("Error loading categories:", error);
            }
        },

        // 2. Create Category
        async createCategory() {
            if (!this.newCategoryName) return;
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

            try {
                const response = await fetch('/api/categories/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify({ name: this.newCategoryName })
                });
                const data = await response.json();
                
                if (data.success) {
                    this.newCategoryName = '';
                    this.fetchCategories();
                } else {
                    alert(data.error);
                }
            } catch (e) { console.error(e); }
        },

        // 3. Delete Category (With Warning)
        async deleteCategory(id, count) {
            let message = "Delete this category?";
            if (count > 0) {
                message = `Wait! This category is used by ${count} goals.\n\nIf you delete it, those goals will become 'Uncategorized'.\n\nProceed?`;
            }

            if (!confirm(message)) return;

            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            try {
                await fetch(`/api/categories/delete/${id}`, { 
                    method: 'POST', 
                    headers: { 'X-CSRFToken': csrfToken }
                });
                this.fetchCategories();
                this.fetchGoals();
            } catch (e) { console.error(e); }
        },

        async advanceStatus(id) {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            await fetch(`/api/advance/${id}`, { method: 'POST', headers: {'X-CSRFToken': csrfToken} });
            this.fetchGoals(); 
            this.calendar.refetchEvents();
        },

        async deleteGoal(id) {
            if(!confirm("Delete this goal permanently?")) return;
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            await fetch(`/api/delete/${id}`, { method: 'POST', headers: {'X-CSRFToken': csrfToken} });
            this.fetchGoals();
            this.calendar.refetchEvents();
        },

        async sendMessage() {
            if (!this.chatInput.trim()) return;
            
            // 1. Show User Message
            const userMsg = this.chatInput;
            this.chatMessages.push({ id: Date.now(), sender: 'user', text: userMsg });
            this.chatInput = '';
            this.isChatting = true;

            // Auto-scroll
            this.$nextTick(() => {
                const container = document.getElementById('chat-container');
                if(container) container.scrollTop = container.scrollHeight;
            });

            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

            // 2. Call Real API
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        goal_id: this.selectedGoal.id,
                        message: userMsg
                    })
                });

                const data = await response.json();
                
                if (data.reply) {
                    // Show AI Response
                    this.chatMessages.push({ id: Date.now() + 1, sender: 'ai', text: data.reply });
                } else {
                    this.chatMessages.push({ id: Date.now() + 1, sender: 'ai', text: data.error || "Error." });
                }
                
            } catch (error) {
                console.error("Chat error:", error);
                this.chatMessages.push({ id: Date.now(), sender: 'ai', text: "Connection error." });
            } finally {
                this.isChatting = false;
                this.$nextTick(() => {
                    const container = document.getElementById('chat-container');
                    if(container) container.scrollTop = container.scrollHeight;
                });
            }
        },

        parseMarkdown(text) {
            if (!text) return '';
            try {
                return marked.parse(text);
            } catch (e) {
                return text;
            }
        },

        // --- CALENDAR LOGIC ---
        initCalendar() {
            let calendarEl = document.getElementById('calendar');
            this.calendar = new FullCalendar.Calendar(calendarEl, {
                initialView: 'dayGridMonth',
                height: 'auto',
                headerToolbar: {
                    left: 'prev,next',
                    center: 'title',
                    right: ''
                },
                
                // Heatmap Logic
                events: async function(info, successCallback, failureCallback) {
                    try {
                        const response = await fetch('/api/goals'); 
                        const allGoals = await response.json();
                        
                        const activeCounts = {}; 
                        const hasCompleted = {};
                        const allDates = new Set();

                        allGoals.forEach(goal => {
                            if (goal.start) {
                                const datePart = goal.start.split('T')[0];
                                allDates.add(datePart);
                                if (goal.status === 'completed') {
                                    hasCompleted[datePart] = true;
                                } else {
                                    activeCounts[datePart] = (activeCounts[datePart] || 0) + 1;
                                }
                            }
                        });
                        
                        const calendarEvents = [];
                        for (const date of allDates) {
                            const active = activeCounts[date] || 0;
                            let dotColor;

                            if (active === 0) {
                                if (hasCompleted[date]) dotColor = '#198754';
                                else continue;
                            } else if (active >= 6) {
                                dotColor = '#dc3545';
                            } else if (active >= 3) {
                                dotColor = '#fd7e14';
                            } else {
                                dotColor = '#3788d8';
                            }
                            
                            calendarEvents.push({
                                start: date,
                                display: 'list-item',
                                color: dotColor
                            });
                        }
                        successCallback(calendarEvents);
                    } catch (e) {
                        failureCallback(e);
                    }
                },
                
                dateClick: (info) => {
                    this.selectDate(info.dateStr, info.dayEl);
                },

                eventClick: (info) => {
                    info.jsEvent.preventDefault();
                    const dateStr = info.event.startStr.split('T')[0];
                    this.selectDate(dateStr, null);
                }
            });
            this.calendar.render();
        },

        selectDate(dateStr, dayEl) {
            this.currentDateFilter = dateStr;
            this.listTitle = `Tasks for ${dateStr}`;
            this.fetchGoals();

            const now = new Date();
            const timeStr = now.toTimeString().slice(0,5); 
            this.newGoalDate = `${dateStr}T${timeStr}`;

            document.querySelectorAll('.fc-day').forEach(el => el.style.backgroundColor = '');
            if (dayEl) {
                dayEl.style.backgroundColor = '#e8f0fe';
            } else {
                const cell = document.querySelector(`.fc-day[data-date="${dateStr}"]`);
                if (cell) cell.style.backgroundColor = '#e8f0fe';
            }
        },
        
        resetFilters() {
            this.currentDateFilter = null;
            this.searchQuery = '';
            this.listTitle = 'All Tasks';
            this.newGoalDate = ''; 
            this.fetchGoals();
            document.querySelectorAll('.fc-day').forEach(el => el.style.backgroundColor = '');
        }
    }
}