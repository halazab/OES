from django import forms
from .models import Exams, Question, Option, ShortAnswer, GradingInterval

class GradingIntervalForm(forms.ModelForm):
    class Meta:
        model = GradingInterval
        fields = ['min_score', 'max_score', 'grade', 'description']
        widgets = {
            'min_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_score': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'grade': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exams
        fields = [
            'title',
            'duration',
            'number_of_questions',
            'total_marks',
            'passing_percentage',
            'description',
            'is_premium',
            'price'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'number_of_questions': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'passing_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'is_premium': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'Exam Title',
            'duration': 'Duration (minutes)',
            'number_of_questions': 'Number of Questions',
            'total_marks': 'Total Marks',
            'passing_percentage': 'Passing Percentage',
            'description': 'Exam Description',
            'is_premium': 'Premium Exam',
            'price': 'Price (if premium)',
        }
        help_texts = {
            'passing_percentage': 'Enter a number between 0 and 100',
            'price': 'Required if exam is premium',
        }

    def clean(self):
        cleaned_data = super().clean()
        is_premium = cleaned_data.get('is_premium')
        price = cleaned_data.get('price')

        if is_premium and (price is None or price <= 0):
            raise forms.ValidationError("Premium exams must have a price greater than 0")
        
        return cleaned_data

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'correct_answer', 'option_a', 'option_b', 'option_c', 'option_d']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': 'Enter your question here'
            }),
            'question_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'correct_answer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the correct answer'
            }),
            'option_a': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Option A'
            }),
            'option_b': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Option B'
            }),
            'option_c': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Option C'
            }),
            'option_d': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Option D'
            }),
        }
        labels = {
            'text': 'Question Text',
            'question_type': 'Question Type',
            'correct_answer': 'Correct Answer',
            'option_a': 'Option A',
            'option_b': 'Option B',
            'option_c': 'Option C',
            'option_d': 'Option D',
        }

    def clean(self):
        cleaned_data = super().clean()
        question_type = cleaned_data.get('question_type')
        
        if question_type == 'MCQ':
            correct = cleaned_data.get('correct_answer')
            options = [
                cleaned_data.get('option_a'),
                cleaned_data.get('option_b'),
                cleaned_data.get('option_c'),
                cleaned_data.get('option_d')
            ]
            if correct not in options:
                raise forms.ValidationError("Correct answer must match one of the options")
        
        elif question_type == 'TF':
            correct = cleaned_data.get('correct_answer').lower()
            if correct not in ['true', 'false']:
                raise forms.ValidationError("True/False questions must have 'True' or 'False' as the correct answer")
        
        return cleaned_data

class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ['question', 'text', 'is_correct']

class ShortAnswerForm(forms.ModelForm):
    class Meta:
        model = ShortAnswer
        fields = ['question', 'correct_answer']